{
    "name": "Mexico - Vehicle Emissions Inspection",
    "version": "2.1",
    "category": "Human Resources/Fleet",
    "summary": "Emissions inspection sticker, windows and checklist per vehicle, from the plate",
    "description": """
Mexican vehicle emissions inspection (verificación vehicular)
=============================================================
The last digit of a vehicle's license plate decides its sticker color (engomado) and its
two yearly inspection windows under the Programa de Verificación Vehicular Obligatoria
(Estado de México / Megalópolis).

* A configurable calendar maps plate digits to a color and its two windows.
* A checklist keeps one inspection per vehicle, year and period, with the appointment,
  the result and the certificate folio.
* Vehicles show their color, window, deadline and inspection status.
""",
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "document_compliance_resource_asset",
        "fleet",
    ],
    "countries": [
        "mx",
    ],
    "data": [
        "data/document_type_data.xml",
        "security/ir.model.access.csv",
        "data/l10n_mx_fleet_emission_calendar_data.xml",
        "data/ir_cron_data.xml",
        "views/l10n_mx_fleet_emission_calendar_views.xml",
        "views/l10n_mx_fleet_emission_inspection_views.xml",
        "views/resource_asset_views.xml",
        "views/l10n_mx_fleet_emission_menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "l10n_mx_fleet_emission/static/src/**/*",
        ],
    },
}
