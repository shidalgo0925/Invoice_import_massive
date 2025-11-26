# Documentación de Cambios - Módulo invoice_import_massive

## Fecha: 2025-11-21

### Problema Identificado

El código estaba usando `invoice.amount_total_signed` (calculado por Odoo) para crear la línea de cuenta por cobrar (`payment_term`), en lugar de usar el total del Excel (`self.total`).

**Problema:**
- Si Odoo no calcula correctamente el total (impuestos faltantes, productos no cargados, etc.), el monto de la línea de cuenta por cobrar será incorrecto
- El total del Excel (`self.total`) es el valor correcto que viene del archivo y debe usarse

**Evidencia:**
- Se encontró una factura (ID 2099) con diferencia de 2820.52 entre el total del Excel y el calculado por Odoo

### Cambio Realizado

**Archivo:** `models/invoice_import_line.py`
**Línea:** 376

**ANTES:**
```python
total_amount = abs(invoice.amount_total_signed)
```

**DESPUÉS:**
```python
# Usar el total del Excel que viene del archivo (es el valor correcto)
# El total del Excel ya viene en positivo si es NCR (convertido en el wizard)
total_amount = abs(self.total)
```

### Puntos de Retorno

1. **Commit de Git:**
   - Commit anterior: `704a8bd` - "Backup antes de modificar: Estado funcional del módulo - versión estable"
   - Commit de backup: `c3d9610` - "Backup antes de cambiar: Usar total del Excel en lugar de amount_total_signed para payment_term"

2. **Archivo de Backup:**
   - `models/invoice_import_line.py.backup_[timestamp]`

### Cómo Revertir

Si necesitas revertir el cambio:

**Opción 1: Usar Git**
```bash
cd /home/ubuntu/invoice_import_massive_git
git checkout HEAD~1 models/invoice_import_line.py
# O volver al commit específico:
git checkout 704a8bd models/invoice_import_line.py
```

**Opción 2: Usar el archivo de backup**
```bash
cd /home/ubuntu/invoice_import_massive_git
cp models/invoice_import_line.py.backup_[timestamp] models/invoice_import_line.py
```

**Opción 3: Restaurar manualmente**
Cambiar la línea 376 de:
```python
total_amount = abs(self.total)
```
a:
```python
total_amount = abs(invoice.amount_total_signed)
```

### Verificación Post-Cambio

Después del cambio, verificar:
1. Que las facturas se crean correctamente
2. Que la línea `payment_term` tiene el monto correcto (debe coincidir con `self.total`)
3. Que no hay errores en los logs de Odoo
4. Que el balance de las facturas es correcto (débito = crédito)

### Notas Adicionales

- El total del Excel ya viene convertido a positivo si es NCR (procesado en el wizard)
- Se mantiene el `abs()` por seguridad, aunque normalmente `self.total` ya debería ser positivo
- Si hay diferencias entre el total del Excel y el calculado por Odoo, se registrará en la línea de cuenta por cobrar (esto es correcto, ya que el Excel es la fuente de verdad)

