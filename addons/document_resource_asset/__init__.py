from . import models


def _document_resource_asset_post_init(env):
    """Carry the fleet's own document settings onto the vehicle kind.

    `document_fleet` kept one folder, one tag set and one switch per company for
    vehicles alone; every kind of asset has them now, as rows.
    """
    cr = env.cr
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_name = 'res_company' AND column_name = 'documents_fleet_folder'
        """
    )
    if not cr.fetchone():
        return
    vehicle = env.ref("resource_asset.kind_vehicle", raise_if_not_found=False)
    if not vehicle:
        return
    cr.execute(
        """
        SELECT id, documents_fleet_settings, documents_fleet_folder
          FROM res_company
         WHERE documents_fleet_folder IS NOT NULL
        """
    )
    settings = env["resource.asset.kind.document"].sudo()
    taken = {
        (setting.kind_id.id, setting.company_id.id)
        for setting in settings.search([("kind_id", "=", vehicle.id)])
    }
    for company_id, centralize, folder_id in cr.fetchall():
        if (vehicle.id, company_id) in taken:
            continue
        cr.execute(
            "SELECT document_tag_id FROM documents_fleet_tags_table WHERE res_company_id = %s",
            [company_id],
        )
        tag_ids = [row[0] for row in cr.fetchall()]
        settings.create(
            {
                "kind_id": vehicle.id,
                "company_id": company_id,
                "centralize": bool(centralize),
                "folder_id": folder_id,
                "tag_ids": [(6, 0, tag_ids)],
            }
        )
