{
    "name": "Dubai Tourism Management",
    "version": "1.0",
    "category": "Services/Tourism",
    "summary": "Manage tour packages, bookings, transportation and payments for a tourism agency",
    "description": """
Dubai Tourism Management
=========================
Manage tour packages, customer bookings, internal vehicles, third-party taxi
partners, payments, discounts and commissions for a tourism agency.
""",
    "depends": ["base", "mail"],
    "data": [
        "security/tourism_security.xml",
        "security/ir.model.access.csv",
        "data/tourism_sequence_data.xml",
        "views/tour_destination_views.xml",
        "views/tour_package_views.xml",
        "views/tour_customer_views.xml",
        "views/tour_vehicle_views.xml",
        "views/tour_taxi_partner_views.xml",
        "views/tour_transport_assignment_views.xml",
        "views/tour_payment_views.xml",
        "views/tour_discount_rule_views.xml",
        "views/tour_commission_views.xml",
        "views/tour_booking_views.xml",
        "views/tourism_reporting_views.xml",
        "views/tourism_menus.xml",
        "data/tourism_demo_data.xml",
    ],
    "application": True,
    "license": "LGPL-3",
}
