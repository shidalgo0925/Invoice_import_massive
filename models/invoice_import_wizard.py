import base64
import io
import pandas as pd
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class InvoiceImportWizard(models.TransientModel):
    _name = 'invoice.import.wizard'
    _description = 'Wizard para Importación Masiva de Facturas'

    file_data = fields.Binary(
        string='Archivo Excel/CSV',
        required=True,
        help='Seleccione un archivo Excel (.xlsx) o CSV (.csv)'
    )
    
    file_name = fields.Char(
        string='Nombre del archivo',
        required=False
    )
    
    file_type = fields.Selection([
        ('excel', 'Excel (.xlsx)'),
        ('csv', 'CSV (.csv)')
    ], string='Tipo de archivo', required=True, default='excel')
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )

    @api.onchange('file_data')
    def _onchange_file_data(self):
        """Detectar automáticamente el tipo de archivo y llenar el nombre"""
        if self.file_data:
            # Obtener el nombre del archivo del contexto si está disponible
            filename = self.env.context.get('filename')
            if filename:
                self.file_name = filename
                # Detectar el tipo de archivo basado en la extensión
                if filename.lower().endswith('.xlsx') or filename.lower().endswith('.xls'):
                    self.file_type = 'excel'
                elif filename.lower().endswith('.csv'):
                    self.file_type = 'csv'
                else:
                    # Si no tiene extensión conocida, detectar por contenido
                    self._detect_file_type_by_content()
            else:
                # Si no hay nombre, detectar por contenido
                self._detect_file_type_by_content()
        else:
            # Limpiar campos si no hay archivo
            self.file_name = False
            self.file_type = 'excel'  # Mantener el valor por defecto

    def _detect_file_type_by_content(self):
        """Detectar el tipo de archivo por su contenido"""
        try:
            import base64
            file_content = base64.b64decode(self.file_data)
            # Verificar si es un archivo Excel (comienza con PK)
            if file_content.startswith(b'PK'):
                self.file_type = 'excel'
                if not self.file_name or not (self.file_name.lower().endswith('.xlsx') or self.file_name.lower().endswith('.xls')):
                    self.file_name = 'archivo_excel.xlsx'
            else:
                # Verificar si es CSV (texto plano)
                try:
                    content_str = file_content.decode('utf-8')
                    if ',' in content_str or ';' in content_str:
                        self.file_type = 'csv'
                        if not self.file_name or not self.file_name.lower().endswith('.csv'):
                            self.file_name = 'archivo_csv.csv'
                    else:
                        # Por defecto, asumir Excel
                        self.file_type = 'excel'
                        if not self.file_name:
                            self.file_name = 'archivo_excel.xlsx'
                except:
                    # Por defecto, asumir Excel
                    self.file_type = 'excel'
                    if not self.file_name:
                        self.file_name = 'archivo_excel.xlsx'
        except:
            # Por defecto, asumir Excel
            self.file_type = 'excel'
            if not self.file_name:
                self.file_name = 'archivo_excel.xlsx'

    @api.constrains('file_data', 'file_name')
    def _check_file_format(self):
        """Validar formato del archivo"""
        for record in self:
            # Solo validar si hay archivo
            if record.file_data:
                # Si no hay nombre, generar uno
                if not record.file_name:
                    if record.file_type == 'excel':
                        record.file_name = 'archivo_excel.xlsx'
                    else:
                        record.file_name = 'archivo_csv.csv'
                
                # Si no hay tipo, detectar por contenido
                if not record.file_type:
                    try:
                        import base64
                        file_content = base64.b64decode(record.file_data)
                        if file_content.startswith(b'PK'):
                            record.file_type = 'excel'
                            if not record.file_name.endswith(('.xlsx', '.xls')):
                                record.file_name = record.file_name + '.xlsx'
                        else:
                            record.file_type = 'csv'
                            if not record.file_name.endswith('.csv'):
                                record.file_name = record.file_name + '.csv'
                    except:
                        # Por defecto Excel
                        record.file_type = 'excel'
                        record.file_name = 'archivo_excel.xlsx'

    def action_process_file(self):
        """Procesar el archivo y crear las facturas automáticamente"""
        self.ensure_one()
        
        if not self.file_data:
            raise UserError(_('Debe seleccionar un archivo para procesar'))
        
        # Si no hay nombre de archivo, generar uno por defecto
        if not self.file_name:
            self.file_name = _('archivo_importacion_%s') % fields.Datetime.now().strftime('%Y%m%d_%H%M%S')
            if self.file_type == 'excel':
                self.file_name += '.xlsx'
            else:
                self.file_name += '.csv'
        
        # Asegurar que el tipo de archivo sea correcto
        if not self.file_type:
            # Intentar detectar por el contenido
            try:
                file_content = base64.b64decode(self.file_data)
                if file_content.startswith(b'PK'):
                    self.file_type = 'excel'
                else:
                    self.file_type = 'csv'
            except:
                self.file_type = 'excel'  # Por defecto Excel
        
        try:
            # Decodificar el archivo
            file_content = base64.b64decode(self.file_data)
            
            # Leer el archivo según el tipo
            if self.file_type == 'excel':
                df = pd.read_excel(io.BytesIO(file_content), na_values=['', 'nan', 'NaN', 'null', 'NULL'])
            else:  # csv
                df = pd.read_csv(io.StringIO(file_content.decode('utf-8')), na_values=['', 'nan', 'NaN', 'null', 'NULL'])
            
            # Limpiar el DataFrame de valores NaN
            df = df.fillna('')
            
            # Crear registro de importación
            import_record = self.env['invoice.import'].create({
                'name': _('Importación %s') % fields.Date.today(),
                'file_name': self.file_name,
                'file_type': self.file_type,
                'company_id': self.company_id.id,
                'state': 'draft'
            })
            
            # Procesar cada línea del archivo
            lines_to_create = []
            for index, row in df.iterrows():
                line_data = self._prepare_line_data(row, index + 1)
                lines_to_create.append((0, 0, line_data))
            
            # Crear las líneas
            import_record.write({
                'import_line_ids': lines_to_create,
                'total_lines': len(df),
                'state': 'validated'
            })
            
            # Procesar automáticamente todas las líneas
            return self._process_all_lines(import_record)
            
        except Exception as e:
            raise UserError(_('Error al procesar el archivo: %s') % str(e))

    def _prepare_line_data(self, row, line_number):
        """Preparar datos de la línea para crear el registro"""
        import pandas as pd
        from datetime import datetime
        
        # Función para limpiar valores NaN
        def clean_value(value, default=''):
            if pd.isna(value) or value == 'nan' or value == 'NaN':
                return default
            return value
        
        # Función para limpiar fechas
        def clean_date(value):
            if pd.isna(value) or value == 'nan' or value == 'NaN' or value == '':
                return fields.Date.today()  # Fecha por defecto
            try:
                if isinstance(value, str):
                    # Intentar parsear diferentes formatos de fecha
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']:
                        try:
                            return datetime.strptime(value, fmt).date()
                        except:
                            continue
                return value
            except:
                return fields.Date.today()
        
        # Función para limpiar números
        def clean_float(value, default=0.0):
            if pd.isna(value) or value == 'nan' or value == 'NaN' or value == '':
                return default
            try:
                return float(value)
            except:
                return default
        
        # Función para limpiar cantidades (mantener negativas para notas de crédito)
        def clean_quantity(value, default=1.0):
            if pd.isna(value) or value == 'nan' or value == 'NaN' or value == '':
                return default
            try:
                qty = float(value)
                # Si la cantidad es 0, usar 1.0 por defecto
                if qty == 0:
                    return default
                # Mantener cantidades negativas para notas de crédito
                return qty
            except:
                return default
        
        # Leer valores del Excel
        comprobante = str(clean_value(row.get('comprobante', '')))
        quantity_raw = clean_quantity(row.get('cantidad', 1.0), 1.0)
        precio_raw = clean_float(row.get('precio', 0.0))
        descuento_raw = clean_float(row.get('descuento', 0.0))
        descuento_porcentaje_raw = clean_float(row.get('descuento_porcentaje', 0.0))
        total_raw = clean_float(row.get('total', 0.0))
        
        # Detectar si es NCR (Nota de Crédito) usando el campo comprobante
        # Si el comprobante NO es "Factura", entonces es NCR
        is_ncr = False
        if comprobante:
            comprobante_lower = comprobante.lower()
            # Normalizar: quitar tildes para comparar
            comprobante_normalized = comprobante_lower.replace('é', 'e').replace('É', 'e')
            # Si NO contiene "factura", entonces es NCR
            if 'factura' not in comprobante_normalized:
                is_ncr = True
        
        # Si es NCR, convertir todos los valores a positivos (Odoo maneja NCR con valores positivos)
        # El indicador interno será move_type = 'out_refund'
        if is_ncr:
            quantity = abs(quantity_raw)
            precio = abs(precio_raw)
            descuento = abs(descuento_raw)
            descuento_porcentaje = abs(descuento_porcentaje_raw) if descuento_porcentaje_raw else 0.0
            total = abs(total_raw)
        else:
            quantity = quantity_raw
            precio = precio_raw
            descuento = descuento_raw
            descuento_porcentaje = descuento_porcentaje_raw
            total = total_raw
        
        return {
            'line_number': line_number,
            'fecha': clean_date(row.get('fecha', '')),
            'comprobante': comprobante,
            'n_interno': str(clean_value(row.get('n_interno', ''))),
            'n_fiscal': str(clean_value(row.get('n_fiscal', ''))),
            'cliente_codigo': str(clean_value(row.get('cliente_codigo', ''))),
            'nombre_cliente': str(clean_value(row.get('nombre_cliente', ''))),
            'razon_social': str(clean_value(row.get('razon_social', ''))),
            'tipo_identificacion': str(clean_value(row.get('tipo_identificacion', ''))),
            'identificacion': str(clean_value(row.get('identificacion', ''))),
            'sucursal': str(clean_value(row.get('sucursal', ''))),
            'vendedor': str(clean_value(row.get('vendedor', ''))),
            'codigo_articulo': str(clean_value(row.get('codigo_articulo', ''))),
            'nombre_articulo': str(clean_value(row.get('nombre_articulo', ''))),
            'referencia': str(clean_value(row.get('referencia', ''))),
            'codigo_barra': str(clean_value(row.get('codigo_barra', ''))),
            'proveedor': str(clean_value(row.get('proveedor', ''))),
            'cuenta': str(clean_value(row.get('cuenta', ''))),
            'quantity': quantity,  # Ya convertido a positivo si es NCR
            'precio': precio,  # Ya convertido a positivo si es NCR
            'descuento': descuento,  # Ya convertido a positivo si es NCR
            'descuento_porcentaje': descuento_porcentaje,  # Ya convertido a positivo si es NCR
            'subtotal_descuento': clean_float(row.get('subtotal_descuento', 0.0)),
            'impuesto': clean_float(row.get('impuesto', 0.0)),
            'impuesto_2': clean_float(row.get('impuesto_2', 0.0)),
            'total': total,  # Ya convertido a positivo si es NCR
            'comentario': str(clean_value(row.get('comentario', ''))),
            'state': 'draft'
        }

    def _process_all_lines(self, import_record):
        """Procesar todas las líneas automáticamente"""
        imported_count = 0
        error_count = 0
        created_clients = 0
        created_products = 0
        created_invoices = 0
        
        # Procesar cada línea
        for line in import_record.import_line_ids:
            try:
                # Validar la línea (crea cliente y producto si no existen)
                line.action_validate_line()
                
                # Contar clientes y productos creados
                if line.partner_id:
                    # Verificar si el cliente fue creado recientemente
                    if line.partner_id.create_date > import_record.create_date:
                        created_clients += 1
                
                if line.product_id:
                    # Verificar si el producto fue creado recientemente
                    if line.product_id.create_date > import_record.create_date:
                        created_products += 1
                
                # Crear la factura
                invoice = line.action_create_invoice()
                if line.state == 'imported':
                    imported_count += 1
                    created_invoices += 1
                else:
                    error_count += 1
                    
            except Exception as e:
                line.write({
                    'state': 'error',
                    'error_message': str(e)
                })
                error_count += 1
        
        # Actualizar estado del import
        final_state = 'imported' if error_count == 0 else 'error'
        import_record.write({
            'state': final_state,
            'imported_lines': imported_count,
            'error_lines': error_count,
            'import_date': fields.Datetime.now()
        })
        
        # Mostrar resumen y abrir la vista de importación
        return self._show_final_summary(import_record, imported_count, error_count, created_clients, created_products, created_invoices)

    def _show_final_summary(self, import_record, imported_count, error_count, created_clients, created_products, created_invoices):
        """Mostrar resumen final y abrir la vista de importación"""
        # Crear mensaje de resumen
        if error_count > 0:
            message = _('Procesamiento completado con advertencias. Facturas: %d, Clientes: %d, Productos: %d, Errores: %d') % (created_invoices, created_clients, created_products, error_count)
        else:
            message = _('¡Procesamiento exitoso! Facturas: %d, Clientes: %d, Productos: %d') % (created_invoices, created_clients, created_products)
        
        # Actualizar el mensaje en el registro de importación
        import_record.write({
            'error_message': message
        })
        
        # Abrir la vista de importación creada
        return {
            'type': 'ir.actions.act_window',
            'name': _('Importación de Facturas - %s') % message,
            'res_model': 'invoice.import',
            'res_id': import_record.id,
            'view_mode': 'form',
            'target': 'current',
        }


