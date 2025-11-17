{
    "name": "Importación Masiva de Facturas",
    "version": "1.0.0",
    "category": "Accounting",
    "summary": "Importación masiva de facturas desde Excel/CSV con validación automática",
    "description": """
        Módulo para importación masiva de facturas desde archivos Excel o CSV.
        
        Características:
        - Carga de archivos Excel/CSV
        - Validación automática de datos
        - Creación automática de clientes y productos
        - Generación de facturas en estado borrador
        - Interfaz intuitiva con ventana emergente
        - Trazabilidad completa del proceso
    """,
    "author": "Easy Technology Services",
    "depends": ["base", "account"],
    "external_dependencies": {
        "python": ["pandas", "openpyxl"]
    },
            "data": [
                "security/ir.model.access.csv",
                "views/invoice_import_views.xml",
                "views/invoice_import_wizard_views.xml",
                "views/account_move_views.xml",
                "views/menu.xml",
            ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3"
}


