from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class InvoiceImport(models.Model):
    _name = 'invoice.import'
    _description = 'Importación Masiva de Facturas'
    _order = 'create_date desc'

    name = fields.Char(
        string='Nombre',
        required=True,
        default=lambda self: _('Importación %s') % fields.Date.today()
    )
    
    file_name = fields.Char(
        string='Nombre del archivo',
        readonly=True
    )
    
    file_type = fields.Selection([
        ('excel', 'Excel (.xlsx)'),
        ('csv', 'CSV (.csv)')
    ], string='Tipo de archivo', readonly=True)
    
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('validated', 'Validado'),
        ('imported', 'Importado'),
        ('error', 'Error')
    ], string='Estado', default='draft', readonly=True)
    
    import_date = fields.Datetime(
        string='Fecha de importación',
        readonly=True
    )
    
    total_lines = fields.Integer(
        string='Total de líneas',
        readonly=True
    )
    
    imported_lines = fields.Integer(
        string='Líneas importadas',
        readonly=True
    )
    
    error_lines = fields.Integer(
        string='Líneas con error',
        readonly=True
    )
    
    total_discount_amount = fields.Float(
        string='Total Descuentos',
        compute='_compute_total_discounts',
        store=True,
        help='Total de descuentos aplicados en todas las líneas'
    )
    
    total_discount_percentage = fields.Float(
        string='Descuento Promedio (%)',
        compute='_compute_total_discounts',
        store=True,
        help='Porcentaje promedio de descuento aplicado'
    )
    
    import_line_ids = fields.One2many(
        'invoice.import.line',
        'import_id',
        string='Líneas de importación'
    )
    
    error_message = fields.Text(
        string='Mensaje de error',
        readonly=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )
    
    @api.depends('import_line_ids.monto_descuento_aplicado', 'import_line_ids.descuento_aplicado')
    def _compute_total_discounts(self):
        """Calcular el total de descuentos aplicados"""
        for record in self:
            total_discount_amount = 0.0
            total_discount_percentage = 0.0
            lines_with_discount = 0
            
            for line in record.import_line_ids:
                if line.monto_descuento_aplicado > 0:
                    total_discount_amount += line.monto_descuento_aplicado
                    total_discount_percentage += line.descuento_aplicado
                    lines_with_discount += 1
            
            record.total_discount_amount = total_discount_amount
            record.total_discount_percentage = total_discount_percentage / lines_with_discount if lines_with_discount > 0 else 0.0

    def action_reset(self):
        """Resetear el import para volver a procesar"""
        self.ensure_one()
        self.write({
            'state': 'draft',
            'import_line_ids': [(5, 0, 0)],
            'total_lines': 0,
            'imported_lines': 0,
            'error_lines': 0,
            'error_message': False
        })

    @api.model
    def action_create_import(self):
        """Crear nueva importación desde el botón de la lista"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Nueva Importación de Facturas'),
            'res_model': 'invoice.import',
            'view_mode': 'form',
            'target': 'current',
            'context': {'default_name': _('Importación %s') % fields.Date.today()}
        }


