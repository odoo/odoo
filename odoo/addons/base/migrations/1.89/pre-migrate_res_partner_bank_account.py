r"""Pre-migration: rename res.partner.bank to res.partner.bank.account.

The model was never a partner's bank. `_description` has read "Bank Accounts"
since before this fork, `_rec_name` is `acc_number`, the unique index is on the
account number, and the lifecycle events the model logs are already spelled
`bank_account_create` / `bank_account_write` / `bank_account_archived`. The name
was the last place still saying otherwise.

It is not res.bank.account either: the prefix in this namespace is the owning
parent -- res.country.state, res.currency.rate, res.users.apikeys -- and the
owner here is the partner (`partner_id` required, ondelete cascade), not the
bank (`bank_id` optional). res.bank also `_inherits` res.partner, so that name
would read as the bank's own account, which is a different thing.

`rename_model` carries the table, its constraints, indexes and sequence, the
derived m2m relation table (res_partner_res_partner_bank_rel), every registry
row, the generated xmlids (`model_`, `field_`, `selection__`, `model_inherit__`,
`constraint_`), every varchar column named like a model reference, stored
Reference values, and the quoted occurrences in domains, contexts, view arches
and server-action code.

Hand-written xmlids are deliberately left alone. `action_res_partner_bank_account_form`
already carries the good name and CONTAINS the old table name as a prefix, so a
substring rewrite would make it `..._bank_account_account_form`; the same is
true of every `res_partner_bank_account_<person>` demo id. The ACL and rule ids
(`access_res_partner_bank_*`, `res_partner_bank_rule`,
`ir_rule_res_partner_bank_*`) stay as they are: their `model_id` reference
follows the renamed `ir.model` xmlid, and renaming the ids themselves would buy
nothing but a second substring trap.
"""

import logging

from odoo.db.schema import table_exists
from odoo.tools.module_data import rename_model

_logger = logging.getLogger(__name__)

OLD_MODEL = "res.partner.bank"
NEW_MODEL = "res.partner.bank.account"
OLD_TABLE = "res_partner_bank"
NEW_TABLE = "res_partner_bank_account"


def migrate(cr, version):
    if not version:
        return

    if not table_exists(cr, OLD_TABLE):
        _logger.info("%s is already gone; nothing to rename.", OLD_TABLE)
        return
    if table_exists(cr, NEW_TABLE):
        raise ValueError(
            f"Both {OLD_TABLE} and {NEW_TABLE} exist. Refusing to guess which "
            f"one holds the bank accounts; resolve by hand."
        )

    relations = rename_model(cr, OLD_MODEL, NEW_MODEL)
    _logger.info(
        "%s renamed to %s, with %d derived join table(s): %s",
        OLD_MODEL,
        NEW_MODEL,
        len(relations),
        ", ".join(f"{old} -> {new}" for old, new in relations.items()) or "none",
    )
