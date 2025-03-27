# See LICENSE file for full copyright and licensing details.

{
    "name": "Transport Management for Education ERP",
    "version": "16.0.1.0.0",
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "website": "http://www.serpentcs.com",
    "license": "AGPL-3",
    "category": "School Management",
    "complexity": "easy",
    "summary": "A Module For Transport & Vehicle Management In School",
    "depends": ["school", "fleet"],
    "images": ["static/description/SchoolTransport.png"],
    "data": [
        "security/transport_security.xml",
        "security/ir.model.access.csv",
        "data/transport_schedular.xml",
        "views/transport_view.xml",
        "report/report_view.xml",
        "report/participants.xml",
        "wizard/transfer_vehicle.xml",
        "wizard/terminate_reason_view.xml",
    ],
    "demo": ["demo/transport_demo.xml"],
    "installable": True,
    "application": True,
}
