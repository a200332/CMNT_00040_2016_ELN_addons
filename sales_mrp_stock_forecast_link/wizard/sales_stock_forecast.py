# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2004-2012 Pexego Sistemas Informáticos All Rights Reserved
#    $Pedro Gómez$ <pegomez@elnogal.com>
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
from openerp.osv import osv
from openerp.tools.translate import _

class sales_stock_forecast(osv.osv_memory):
    _name = 'sales.stock.forecast'

    def generate_forecast(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if context.get('active_ids', False):
            for cur in self.pool.get('sales.forecast').browse(cr, uid, context['active_ids'], context):
                self.pool.get('sales.forecast').generate_stock_forecast(cr, uid, cur.id, context)
        else:
            raise osv.except_osv(_('Error !'), _('You must select at least one forecast.'))
        
        return {'type': 'ir.actions.act_window_close'}
