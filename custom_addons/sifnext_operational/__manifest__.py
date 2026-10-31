{
    "name": "SIFNEXT Operational",
    "version": "1.0.0",
    "summary": "Modul Operasional ERP SIFNEXT",
    "description": """
        Modul Operational ERP SIFNEXT.

        Mencakup:
        - Peminjaman Ruangan
        - Peminjaman Kendaraan Dinas
        - Pengecekan Ketersediaan
        - Approval General Affair
        - Booking Jadwal
    """,
    "category": "Operations",
    "author": "SIFNEXT IT",
    "license": "LGPL-3",

    "depends": [
        "base",
        "mail",
    ],

    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",

        "data/sequence.xml",
        "data/room_data.xml",
        "data/vehicle_data.xml",

        "views/operational_views.xml",
        "views/room_views.xml",
        "views/room_booking_views.xml",
        "views/vehicle_booking_views.xml",
        "views/vehicle_views.xml",
        "views/user_role_views.xml",
    ],

    "assets": {
        "web.assets_backend": [
            "sifnext_operational/static/src/css/operational.css",
        ],
    },

    "installable": True,
    "application": True,
}