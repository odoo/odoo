# Copyright 2021 Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)

map_payment_methods = [
    ("payment_method_efectivo", "payment_method_efectivo"),
    ("payment_method_cheque", "payment_method_cheque"),
    ("payment_method_transferencia", "payment_method_transferencia"),
    ("payment_method_tarjeta_de_credito", "payment_method_tarjeta_de_credito"),
    ("payment_method_monedero_electronico", "payment_method_monedero_electronico"),
    ("payment_method_dinero_electronico", "payment_method_dinero_electronico"),
    ("payment_method_vales_despensa", "payment_method_vales_despensa"),
    ("payment_method_12", "payment_method_12"),
    ("payment_method_13", "payment_method_13"),
    ("payment_method_14", "payment_method_14"),
    ("payment_method_15", "payment_method_15"),
    ("payment_method_17", "payment_method_17"),
    ("payment_method_23", "payment_method_23"),
    ("payment_method_24", "payment_method_24"),
    ("payment_method_25", "payment_method_25"),
    ("payment_method_26", "payment_method_26"),
    ("payment_method_27", "payment_method_27"),
    ("payment_method_tarjeta_debito", "payment_method_tarjeta_debito"),
    ("payment_method_tarjeta_servicio", "payment_method_tarjeta_servicio"),
    ("payment_method_30", "payment_method_anticipos"),
    ("payment_method_otros", "payment_method_otros"),
]

def fix_sat_codes(env):
    _logger.warning('Change SAT codes external ids')
    env.cr.execute("""
        UPDATE ir_model_data dest
        SET module = 'product_unspsc', model = 'product.unspsc.code', name = CONCAT('unspsc_code_', SPLIT_PART(src.name, '_', 6))
        FROM ir_model_data src
        WHERE src.id = dest.id AND src.model = 'l10n_mx_edi.product.sat.code';
    """)

@openupgrade.migrate()
def migrate(env, installed_version):
    _logger.warning('Start Migration')
    _logger.warning('Remove account types with no internal group')
    env.cr.execute("""
        DELETE FROM account_account_type
        WHERE internal_group IS NULL;
    """)
    _logger.warning('Remove data from l10n_mx_base that causes error')
    env.cr.execute("""
        DELETE FROM ir_model_access WHERE group_id = 6;
    """)
    env.cr.execute("""
        DELETE FROM res_groups WHERE id = 90;
    """)
    env.cr.execute("""
        SELECT id
        FROM ir_act_server
        WHERE name IN ('Ping PAC server', 'Check Account Color Tag')
    """)
    action_server_ids = env.cr.fetchall()
    env.cr.execute("""
        DELETE FROM base_automation WHERE action_server_id IN %(action_server_ids)s;
    """, {
        'action_server_ids': tuple(action_server_ids),
    })
    _logger.warning('Update payment methods model data')
    for method in map_payment_methods:
        env.cr.execute("""
            UPDATE ir_model_data 
            SET name = %s, model = 'l10n_mx_edi.payment.method', module = 'l10n_mx_edi'
            WHERE model = 'l10n_mx.payment.method' AND name = %s;
        """, (method[1], method[0]))