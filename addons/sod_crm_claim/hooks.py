# Copyright 2019-2023 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


# Commented to support multi company
# def post_init_hook(cr, registry):
#     env = api.Environment(cr, SUPERUSER_ID, {})
#     warehouse = env.ref("stock.warehouse0")
#     rma_type_id = env.ref("sod_crm_claim.picking_type_rma").id
#     warehouse.write(
#         {
#             "rma_type_id": rma_type_id,
#         }
#     )


def pre_init_hook(cr):
    # Preserve key data when moving from crm_claim to sod_crm_claim
    # The process is to first install sod_crm_claim
    # and then uninstall crm_claim
    query_claim_model_data = "select 1 from ir_model_data where module = 'crm_claim';"
    cr.execute(query_claim_model_data)
    crm_clam_model_data = cr.dictfetchall()
    query_update_crm_claim_data = """
        update
            ir_model_data
        set
            module='sod_crm_claim'
        where
            module = 'crm_claim'
        returning id;
    """
    if len(crm_clam_model_data):
        cr.execute(query_update_crm_claim_data)
        _logger.info(str(cr.dictfetchall()))
