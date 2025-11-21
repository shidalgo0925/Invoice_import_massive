# Invoice Import Massive - Odoo 18

Módulo para importación masiva de facturas desde archivos Excel/CSV en Odoo 18.

## Características

- ✅ Carga de archivos Excel (.xlsx) o CSV (.csv)
- ✅ Validación automática de datos
- ✅ Creación automática de clientes y productos
- ✅ Generación de facturas en estado borrador
- ✅ Manejo de descuentos (monto y porcentaje)
- ✅ Soporte para notas de crédito
- ✅ Trazabilidad completa del proceso

## Dependencias

### Python
- `pandas`
- `openpyxl`

### Odoo
- `base`
- `account`

## Instalación

1. Copiar el módulo a la carpeta de addons personalizados:
```bash
cp -r invoice_import_massive /opt/odoo/custom-addons/
```

2. Instalar las dependencias Python:
```bash
pip install pandas openpyxl
```

3. Actualizar la lista de aplicaciones en Odoo y instalar el módulo "Importación Masiva de Facturas"

## Uso

1. Ir a **Contabilidad > Importación Masiva de Facturas > Cargar Factura**
2. Seleccionar archivo Excel o CSV
3. El sistema procesará automáticamente el archivo y creará las facturas

## Estructura del archivo Excel/CSV

El archivo debe contener las siguientes columnas:

- `fecha` - Fecha de la factura
- `comprobante` - Tipo de comprobante
- `n_interno` - Número interno
- `n_fiscal` - Número fiscal
- `cliente_codigo` - Código del cliente
- `nombre_cliente` - Nombre del cliente
- `razon_social` - Razón social
- `identificacion` - Identificación fiscal
- `codigo_articulo` - Código del artículo
- `nombre_articulo` - Nombre del artículo
- `cantidad` - Cantidad
- `precio` - Precio unitario
- `descuento` - Descuento (monto)
- `descuento_porcentaje` - Descuento (%)
- `total` - Total
- `cuenta` - Código de cuenta contable (opcional)

## Autor

Easy Technology Services

## Licencia

LGPL-3








