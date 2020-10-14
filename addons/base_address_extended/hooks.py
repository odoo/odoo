# Part of Odoo. See LICENSE file for full copyright and licensing details.


# Define for each format a tuple with the format, and the codes for countries
# using that format. The dictionary keys are only for documentation.
COUNTRY_FORMATS = {
    "street_first": (
        "%(street_name)s %(street_number)s/%(street_number2)s",
        ("BE", "CH", "DE", "ES", "FI", "GR", "MX", "NL", "NO", "SE"),
    ),
    "street_first_blank_before_door": (
        "%(street_name)s %(street_number)s %(street_number2)s",
        ("HR", ),
    ),
}


def pre_init_hook(cr):
    """Pre-add column street_format, so we can set value before street fields are set.

    We will only set the desired value for street_format for countries that do not
    have them set already.

    TODO: Add defaults for other countries and other formats.
    """
    try:
        cr.execute("ALTER TABLE res_country ADD COLUMN street_format VARCHAR")
    except Exception:
        # Apparently field already in database
        pass
    for (street_format, country_codes) in COUNTRY_FORMATS.values():
        # Only update street_format if not already set.
        cr.execute(
            "UPDATE res_country"
            " SET street_format = %s"
            " WHERE code IN %s AND street_format IS NULL",
            (street_format, country_codes)
        )
