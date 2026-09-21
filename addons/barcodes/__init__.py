from . import models


def _update_default_nomenclature(env):
    companies_without_nomenclature = env["res.company"].search(
        [("barcodes_config_id.nomenclature_id", "=", False)]
    )
    default_nomenclature = env.ref(
        "barcodes.default_barcode_nomenclature", raise_if_not_found=False
    )
    if default_nomenclature:
        companies_without_nomenclature.barcodes_config_id.nomenclature_id = (
            default_nomenclature
        )
