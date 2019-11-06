# Copyright 2019 Quartile Limted, Timeware Limited
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = "account.payment"

    sale_order_ids = fields.Many2many(
        'sale.order',
        compute = '_get_sale_order_ref',
        store=True,
        search = '_search_by_so'
    )
    sale_order_id = fields.Char(
        'Sale Order',
        related = 'sale_order_ids.display_name',
    )
    payment_info = fields.Char(
        'Payment Info',
    )
    payment_reviewed = fields.Boolean(
        'Checked',
    )

    def _search_by_so(self,operator,value):
        return [('sale_order_id', operator, value)]

    @api.multi
    def _get_sale_order_ref(self):
        for payment in self:
            sale_order_ids = payment.mapped('reconciled_invoice_ids').mapped('invoice_line_ids').mapped('sale_line_ids').mapped('order_id')
            if len(sale_order_ids) == 1:
                payment.sale_order_ids = sale_order_ids

    @api.multi
    def action_orders_2(self):
        view_id = self.env.ref('account.view_account_payment_form').id
        id = self.id
        return {
            'name': 'Customer Payments',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'account.payment',
            'view_id': view_id,
            'res_id': id,
            'target': 'current',
            'type': 'ir.actions.act_window',
        }
