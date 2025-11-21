from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class InvoiceImportLine(models.Model):
    _name = 'invoice.import.line'
    _description = 'Línea de Importación de Factura'
    _order = 'line_number'

    import_id = fields.Many2one(
        'invoice.import',
        string='Importación',
        required=True,
        ondelete='cascade'
    )
    
    line_number = fields.Integer(
        string='Número de línea',
        required=True
    )
    
    # Datos del archivo original
    fecha = fields.Date(string='Fecha', required=True)
    comprobante = fields.Char(string='Comprobante', required=True)
    n_interno = fields.Char(string='Número Interno', required=True)
    n_fiscal = fields.Char(string='Número Fiscal', required=True)
    cliente_codigo = fields.Char(string='Código Cliente', required=True)
    nombre_cliente = fields.Char(string='Nombre Cliente', required=True)
    razon_social = fields.Char(string='Razón Social')
    tipo_identificacion = fields.Char(string='Tipo Identificación')
    identificacion = fields.Char(string='Identificación', required=True)
    sucursal = fields.Char(string='Sucursal')
    vendedor = fields.Char(string='Vendedor')
    codigo_articulo = fields.Char(string='Código Artículo', required=True)
    nombre_articulo = fields.Char(string='Nombre Artículo', required=True)
    referencia = fields.Char(string='Referencia')
    codigo_barra = fields.Char(string='Código de Barra')
    proveedor = fields.Char(string='Proveedor')
    cuenta = fields.Char(string='Cuenta')
    quantity = fields.Float(string='Cantidad', default=1.0, required=True)
    precio = fields.Float(string='Precio', required=True)
    descuento = fields.Float(string='Descuento (Monto)', default=0.0, help='Monto del descuento en valor absoluto')
    descuento_porcentaje = fields.Float(string='Descuento (%)', default=0.0, help='Porcentaje de descuento')
    subtotal_descuento = fields.Float(string='Subtotal con Descuento', compute='_compute_subtotal_descuento', store=True)
    descuento_aplicado = fields.Float(string='Descuento Aplicado (%)', readonly=True, help='Porcentaje de descuento aplicado en la factura')
    monto_descuento_aplicado = fields.Float(string='Monto Descuento Aplicado', readonly=True, compute='_compute_monto_descuento_aplicado', help='Monto del descuento aplicado en la factura')
    impuesto = fields.Float(string='Impuesto', default=0.0)
    impuesto_2 = fields.Float(string='Impuesto 2', default=0.0)
    total = fields.Float(string='Total', required=True)
    comentario = fields.Text(string='Comentario')
    
    # Campos calculados y relaciones
    partner_id = fields.Many2one('res.partner', string='Cliente', readonly=True)
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    account_id = fields.Many2one('account.account', string='Cuenta Contable', help='Cuenta contable para esta línea de factura')
    
    # Estado y factura creada
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('validated', 'Validado'),
        ('imported', 'Importado'),
        ('error', 'Error')
    ], string='Estado', default='draft', readonly=True)
    
    invoice_id = fields.Many2one('account.move', string='Factura Creada', readonly=True)
    error_message = fields.Text(string='Mensaje de error', readonly=True)
    company_id = fields.Many2one('res.company', string='Compañía', related='import_id.company_id', store=True)

    @api.depends('quantity', 'precio', 'descuento', 'descuento_porcentaje')
    def _compute_subtotal_descuento(self):
        """Calcular el subtotal con descuento"""
        for line in self:
            # Los valores ya vienen positivos (convertidos en el wizard si es NCR)
            subtotal = line.quantity * line.precio
            
            # Calcular descuento por monto o porcentaje (todos los valores son positivos)
            descuento_por_monto = 0.0
            
            if line.descuento and line.descuento > 0.0:
                # Usar monto del descuento directamente (ya viene positivo)
                descuento_por_monto = line.descuento
            elif line.descuento_porcentaje and line.descuento_porcentaje > 0.0:
                # Calcular monto basado en porcentaje (ya viene positivo)
                descuento_por_monto = subtotal * (line.descuento_porcentaje / 100)
            
            # Aplicar el descuento (todos los valores son positivos)
            line.subtotal_descuento = subtotal - descuento_por_monto
    
    @api.depends('quantity', 'precio', 'descuento_aplicado')
    def _compute_monto_descuento_aplicado(self):
        """Calcular el monto del descuento aplicado"""
        for line in self:
            # Los valores ya vienen positivos (convertidos en el wizard si es NCR)
            if line.descuento_aplicado and line.descuento_aplicado > 0.0:
                subtotal = line.quantity * line.precio
                # Calcular el monto del descuento (todos los valores son positivos)
                line.monto_descuento_aplicado = subtotal * (line.descuento_aplicado / 100)
            else:
                line.monto_descuento_aplicado = 0.0

    @api.constrains('quantity', 'precio')
    def _check_positive_amounts(self):
        """Validar que las cantidades y precios sean válidos"""
        for line in self:
            # Permitir cantidades negativas para notas de crédito
            if line.quantity == 0:
                raise ValidationError(_('La cantidad no puede ser 0'))
            # Permitir precios negativos para notas de crédito
            # No validar precios negativos ya que pueden ser válidos en NCR

    def action_validate_line(self):
        """Validar la línea individual"""
        self.ensure_one()
        
        try:
            # Buscar o crear el partner
            partner = self._find_or_create_partner()
            if not partner:
                raise UserError(_('No se pudo encontrar o crear el cliente: %s') % self.nombre_cliente)
            
            # Buscar o crear el producto
            product = self._find_or_create_product()
            if not product:
                raise UserError(_('No se pudo encontrar o crear el producto: %s') % self.nombre_articulo)
            
            self.write({
                'partner_id': partner.id,
                'product_id': product.id,
                'state': 'validated'
            })
        except Exception as e:
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            raise

    def _find_or_create_partner(self):
        """Buscar o crear el partner"""
        # Buscar por identificación primero
        if self.identificacion:
            partner = self.env['res.partner'].search([
                ('vat', '=', self.identificacion),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            if partner:
                return partner
        
        # Buscar por código de cliente
        if self.cliente_codigo:
            partner = self.env['res.partner'].search([
                ('ref', '=', self.cliente_codigo),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            if partner:
                return partner
        
        # Buscar por nombre
        partner = self.env['res.partner'].search([
            ('name', 'ilike', self.nombre_cliente),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if partner:
            return partner
        
        # Crear nuevo partner
        partner_vals = {
            'name': self.nombre_cliente or self.razon_social,
            'company_id': self.company_id.id,
            'is_company': True,
        }
        
        if self.identificacion:
            partner_vals['vat'] = self.identificacion
        
        if self.cliente_codigo:
            partner_vals['ref'] = self.cliente_codigo
        
        return self.env['res.partner'].create(partner_vals)

    def _find_or_create_product(self):
        """Buscar o crear el producto"""
        # Buscar por código de artículo primero
        if self.codigo_articulo:
            product = self.env['product.product'].search([
                ('default_code', '=', self.codigo_articulo),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            if product:
                return product
        
        # Buscar por código de barra
        if self.codigo_barra:
            product = self.env['product.product'].search([
                ('barcode', '=', self.codigo_barra),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            if product:
                return product
        
        # Buscar por nombre exacto
        product = self.env['product.product'].search([
            ('name', '=', self.nombre_articulo),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if product:
            return product
        
        # Crear nuevo producto
        product_vals = {
            'name': self.nombre_articulo,
            'type': 'consu',  # En Odoo 18: 'consu' para bienes tangibles
            'company_id': self.company_id.id,
            'list_price': self.precio,
        }
        
        if self.codigo_articulo:
            product_vals['default_code'] = self.codigo_articulo
        
        if self.codigo_barra:
            product_vals['barcode'] = self.codigo_barra
        
        return self.env['product.product'].create(product_vals)

    def action_create_invoice(self):
        """Crear la factura desde la línea"""
        self.ensure_one()
        
        try:
            if self.state != 'validated':
                self.action_validate_line()
            
            if not self.partner_id:
                raise UserError(_('No se pudo validar el cliente'))
            
            if not self.product_id:
                raise UserError(_('No se pudo validar el producto'))
            
            # Obtener el diario de facturas de cliente
            journal = self.env['account.journal'].search([
                ('type', '=', 'sale'),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            
            if not journal:
                raise UserError(_('No se encontró un diario de ventas configurado'))
            
            # Determinar el tipo de documento
            # IMPORTANTE: Los valores ya vienen convertidos a positivos desde el wizard si es NCR
            move_type = 'out_invoice'  # Factura por defecto
            
            # Detectar si es una nota de crédito usando el campo comprobante
            # Si el comprobante NO es "Factura", entonces es NCR
            if self.comprobante:
                comprobante_lower = self.comprobante.lower()
                # Normalizar: quitar tildes para comparar
                comprobante_normalized = comprobante_lower.replace('é', 'e').replace('É', 'e')
                # Si NO contiene "factura", entonces es NCR
                if 'factura' not in comprobante_normalized:
                    move_type = 'out_refund'  # Nota de crédito (código interno para NCR)
            
            # Los valores ya están en positivo (convertidos en el wizard si es NCR)
            quantity = self.quantity  # Ya viene positivo del wizard
            price_unit = self.precio  # Ya viene positivo del wizard
            
            # Calcular el descuento a aplicar
            # IMPORTANTE: Todos los valores ya están en positivo (convertidos en el wizard)
            # El descuento ya viene positivo si es NCR, así que trabajamos igual para facturas y NCR
            discount_percentage = 0.0
            subtotal_base = quantity * price_unit
            
            # Calcular el porcentaje de descuento
            if subtotal_base != 0.0:
                # Si hay monto de descuento, calcular el porcentaje
                if self.descuento and self.descuento > 0.0:
                    # Calcular porcentaje basado en el monto del descuento (ya está positivo)
                    discount_percentage = (self.descuento / subtotal_base) * 100
                # Si no hay monto pero hay porcentaje, usar el porcentaje directamente
                elif self.descuento_porcentaje and self.descuento_porcentaje > 0.0:
                    # El porcentaje ya viene positivo (convertido en el wizard si es NCR)
                    discount_percentage = self.descuento_porcentaje
            
            # IMPORTANTE: Guardar el porcentaje calculado ANTES de crear la factura
            # Esto permite que los campos computados puedan usar el porcentaje
            if discount_percentage > 0.0:
                # Guardar el porcentaje calculado
                self.descuento_porcentaje = discount_percentage
                self.descuento_aplicado = discount_percentage
            
            # Usar la cuenta contable del Excel (campo cuenta)
            account_id = None
            if self.cuenta:
                # Buscar la cuenta contable por código
                # Intentar primero con el campo code directamente
                account = self.env['account.account'].search([
                    ('code', '=', self.cuenta),
                    ('company_id', '=', self.company_id.id)
                ], limit=1)
                # Si no se encuentra, intentar con code_store (formato JSON en Odoo 18)
                if not account:
                    account = self.env['account.account'].search([
                        ('code_store->>1', '=', self.cuenta),
                        ('company_id', '=', self.company_id.id)
                    ], limit=1)
                if account:
                    account_id = account.id
                else:
                    # Si no se encuentra la cuenta, usar la cuenta por defecto del producto
                    account_id = self.product_id.property_account_income_id.id if self.product_id.property_account_income_id else None
            elif self.account_id:
                # Usar la cuenta contable especificada manualmente
                account_id = self.account_id.id
            
            # Preparar datos de la factura
            invoice_line_vals = {
                'product_id': self.product_id.id,
                'quantity': quantity,
                'price_unit': price_unit,
                'name': self.nombre_articulo,
                'discount': discount_percentage,
            }
            
            # Agregar cuenta contable si está disponible
            if account_id:
                invoice_line_vals['account_id'] = account_id
            
            invoice_vals = {
                'move_type': move_type,
                'partner_id': self.partner_id.id,
                'invoice_date': self.fecha,
                'ref': self.n_interno,
                'journal_id': journal.id,
                'company_id': self.company_id.id,
                'invoice_line_ids': [(0, 0, invoice_line_vals)]
            }
            
            # Crear la factura
            invoice = self.env['account.move'].create(invoice_vals)
            
            # Forzar el recálculo de la factura para asegurar que el descuento se aplique
            invoice._compute_amount()
            invoice._compute_amount_tax()
            
            # Forzar el recálculo de las líneas de factura
            for line in invoice.invoice_line_ids:
                line._compute_price_subtotal()
                line._compute_price_total()
            
            # Actualizar la línea con la factura creada
            # El porcentaje ya se guardó antes de crear la factura
            self.write({
                'invoice_id': invoice.id,
                'state': 'imported'
            })
            
            return invoice
            
        except Exception as e:
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            raise

    def action_view_invoice(self):
        """Ver la factura creada"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_('No hay factura asociada a esta línea'))
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Factura'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    
    def action_verify_discount(self):
        """Verificar que el descuento se aplicó correctamente en la factura"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_('No hay factura asociada a esta línea'))
        
        # Buscar la línea de factura correspondiente
        invoice_line = self.invoice_id.invoice_line_ids.filtered(
            lambda l: l.product_id == self.product_id and l.name == self.nombre_articulo
        )
        
        if not invoice_line:
            raise UserError(_('No se encontró la línea correspondiente en la factura'))
        
        # Verificar el descuento aplicado
        discount_applied = invoice_line.discount
        expected_discount = self.descuento_aplicado
        
        # Calcular montos de descuento
        subtotal = abs(self.quantity) * abs(self.precio)
        expected_discount_amount = subtotal * (expected_discount / 100) if expected_discount > 0 else 0
        applied_discount_amount = subtotal * (discount_applied / 100) if discount_applied > 0 else 0
        
        message = f"""
        Descuento esperado: {expected_discount}% (${expected_discount_amount:.2f})
        Descuento aplicado en factura: {discount_applied}% (${applied_discount_amount:.2f})
        """
        
        if abs(discount_applied - expected_discount) < 0.01:  # Tolerancia de 0.01%
            message += "\n✅ El descuento se aplicó correctamente"
        else:
            message += "\n❌ El descuento NO se aplicó correctamente"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Verificación de Descuento'),
                'message': message,
                'type': 'success' if abs(discount_applied - expected_discount) < 0.01 else 'warning',
                'sticky': True,
            }
        }
    
    def action_debug_discount(self):
        """Método de depuración para verificar descuentos"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_('No hay factura asociada a esta línea'))
        
        # Buscar la línea de factura correspondiente
        invoice_line = self.invoice_id.invoice_line_ids.filtered(
            lambda l: l.product_id == self.product_id and l.name == self.nombre_articulo
        )
        
        if not invoice_line:
            raise UserError(_('No se encontró la línea correspondiente en la factura'))
        
        # Información detallada
        message = f"""
        === INFORMACIÓN DE DESCUENTO ===
        
        LÍNEA DE IMPORTACIÓN:
        - Descuento (monto): ${self.descuento:.2f}
        - Descuento porcentaje: {self.descuento_porcentaje}%
        - Descuento aplicado: {self.descuento_aplicado}%
        - Monto descuento aplicado: ${self.monto_descuento_aplicado:.2f}
        
        LÍNEA DE FACTURA:
        - Descuento: {invoice_line.discount}%
        - Precio unitario: ${invoice_line.price_unit:.2f}
        - Cantidad: {invoice_line.quantity}
        - Subtotal: ${invoice_line.price_subtotal:.2f}
        - Total: ${invoice_line.price_total:.2f}
        
        CÁLCULOS:
        - Subtotal sin descuento: ${abs(self.quantity) * abs(self.precio):.2f}
        - Descuento calculado: ${(abs(self.quantity) * abs(self.precio)) * (self.descuento_aplicado / 100):.2f}
        """
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Depuración de Descuento'),
                'message': message,
                'type': 'info',
                'sticky': True,
            }
        }
    
    def action_update_invoice_discount(self):
        """Actualizar el descuento en la factura existente"""
        self.ensure_one()
        
        if not self.invoice_id:
            raise UserError(_('No hay factura asociada a esta línea'))
        
        # Buscar la línea de factura correspondiente
        invoice_line = self.invoice_id.invoice_line_ids.filtered(
            lambda l: l.product_id == self.product_id and l.name == self.nombre_articulo
        )
        
        if not invoice_line:
            raise UserError(_('No se encontró la línea correspondiente en la factura'))
        
        # Actualizar el descuento en la línea de factura
        invoice_line.write({
            'discount': self.descuento_aplicado
        })
        
        # Forzar el recálculo de la línea de factura
        invoice_line._compute_price_subtotal()
        invoice_line._compute_price_total()
        
        # Forzar el recálculo de la factura
        self.invoice_id._compute_amount()
        self.invoice_id._compute_amount_tax()
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Factura Actualizada'),
                'message': f'El descuento se actualizó correctamente en la factura.\nDescuento: {self.descuento_aplicado}% (${self.monto_descuento_aplicado:.2f})',
                'type': 'success',
                'sticky': True,
            }
        }


