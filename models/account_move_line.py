from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    discount_amount = fields.Float(
        string='Monto Descuento',
        compute='_compute_discount_amount',
        store=True,
        help='Monto del descuento en valor absoluto'
    )

    @api.depends('discount', 'price_unit', 'quantity')
    def _compute_discount_amount(self):
        """Calcular el monto del descuento"""
        for line in self:
            if line.discount > 0:
                subtotal = line.price_unit * line.quantity
                line.discount_amount = subtotal * (line.discount / 100)
            else:
                line.discount_amount = 0.0


class AccountMove(models.Model):
    _inherit = 'account.move'

    total_discount_amount = fields.Float(
        string='Total Descuentos',
        compute='_compute_total_discount_amount',
        store=True,
        help='Total de descuentos aplicados en todas las líneas'
    )

    @api.depends('invoice_line_ids.discount_amount')
    def _compute_total_discount_amount(self):
        """Calcular el total de descuentos de la factura"""
        for move in self:
            move.total_discount_amount = sum(move.invoice_line_ids.mapped('discount_amount'))
