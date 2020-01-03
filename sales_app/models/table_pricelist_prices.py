# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015-2018 Coimunitea Servicios Tecnológicos All Rights Reserved
#    $Javier Colmenero Fernández$ <javier@comunitea.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models, fields, api
from openerp.tools import float_compare
import openerp.addons.decimal_precision as dp


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    sale_app = fields.Boolean('Sale in app')


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    in_app = fields.Boolean('Pricelist in APP', default=False)

    @api.model
    def _price_rule_get_multi(self, pricelist, products_by_qty_by_partner):
        if self._context.get('from_sales_app', False):
            date = self._context.get('date') or fields.Date.context_today(self)
            date = date[0:10]
            products = map(lambda x: x[0], products_by_qty_by_partner)
            if not products:
                return {}
            version = False
            for v in pricelist.version_id:
                if ((v.date_start is False) or (v.date_start <= date)) and ((v.date_end is False) or (v.date_end >= date)):
                    version = v
                    break
            if not version:
                res = {}
                for product in products:
                    res[product.id] = (False, False)
                return res
        return super(ProductPricelist, self)._price_rule_get_multi(pricelist, products_by_qty_by_partner)


class TablePricelistPrices(models.Model):
    _name = 'table.pricelist.prices'
    _rec_name = 'pricelist_id'

    pricelist_id = fields.Many2one(
        'product.pricelist', 'Pricelist',
        readonly=True)
    product_id = fields.Many2one(
        'product.product', 'Product',
        readonly=True)
    price = fields.Float('Price',
        digits=dp.get_precision('Product Price'),
        readonly=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        readonly=True)

    @api.one
    def recalculate_table_btn(self):
        return self.recalculate_table()

    @api.model
    def recalculate_table(self):
        t_product = self.env['product.product']
        t_pricelist = self.env['product.pricelist']
        t_company = self.env['res.company']
        domain = [('sale_ok', '=', True)]
        prod_objs = t_product.search(domain)
        domain = [('type', '=', 'sale'), ('in_app', '=', True)]
        pricelist_objs = t_pricelist.search(domain, order='id')
        table = {}  
        for product in prod_objs:
            if not product.id in table.keys():
                table[product.id] = {}
            for pricelist in pricelist_objs:
                default_company = pricelist.company_id.id or self.env.user.company_id.id
                domain = [('parent_id', 'child_of', [default_company])]
                company_ids = t_company.search(domain)
                if not pricelist.id in table[product.id].keys():
                    table[product.id][pricelist.id] = {}
                for company_id in company_ids:
                    price = pricelist.with_context(from_sales_app=True).price_get_multi(
                        products_by_qty_by_partner=[
                            (product.with_context(force_company=company_id.id), 1.0, False)
                    ])
                    table[product.id][pricelist.id][company_id.id] = \
                        price and price[product.id][pricelist.id] or 0.0
        for product in prod_objs:
            product_table = table and table[product.id] or {}
            for pricelist in pricelist_objs:
                if pricelist.id in product_table.keys():
                    for company_id in product_table[pricelist.id].keys():
                        price = product_table[pricelist.id][company_id]
                        if not price or price < 0.0:
                            price = 0.0
                        domain = [
                            ('product_id', '=', product.id),
                            ('pricelist_id', '=', pricelist.id),
                            ('company_id', '=', company_id)
                        ]
                        rec_table = self.search(domain, limit=1)
                        if not rec_table and price > 0.0:
                            vals = {
                                'product_id': product.id,
                                'pricelist_id': pricelist.id,
                                'price': price,
                                'company_id': company_id
                            }
                            self.create(vals)
                        else:
                            precision_digits = dp.get_precision('Product Price')(self.env.cr)[1]
                            compare = float_compare(price, rec_table.price, precision_digits=precision_digits)
                            if compare != 0:
                                rec_table.price = price
        # Borro todo lo que sobra (precios a 0, productos no vendibles, tarifas de precios no en app)
        sql = """
            delete from table_pricelist_prices
            where price <= 0.00
                or pricelist_id not in (select id from product_pricelist where in_app = True)
                or product_id not in (select pp.id from product_product pp inner join product_template pt on pt.id = pp.product_tmpl_id where pt.sale_ok = True)
        """
        self._cr.execute(sql)
        return True
