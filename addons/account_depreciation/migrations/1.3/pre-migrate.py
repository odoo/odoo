from odoo.tools import SQL
from odoo.tools.module_data import rename_field, rename_in_stored_expressions

ASSET_FIELDS = {
    "state": "depreciation_state",
    "method": "depreciation_method",
    "method_number": "depreciation_duration",
    "method_period": "depreciation_period",
    "method_progress_factor": "depreciation_factor",
    "prorata_computation_type": "depreciation_prorata",
    "prorata_date": "date_prorata",
    "paused_prorata_date": "date_prorata_paused",
    "acquisition_date": "date_acquisition",
    "disposal_date": "date_disposal",
    "original_value": "value_original",
    "book_value": "value_book",
    "value_residual": "value_depreciable_residual",
    "total_depreciable_value": "value_depreciable",
    "salvage_value": "value_salvage",
    "gross_increase_value": "value_increase",
    "non_deductible_tax_value": "value_non_deductible_tax",
    "related_purchase_value": "value_purchase",
    "already_depreciated_amount_import": "value_depreciated_import",
    "net_gain_on_sale": "value_gain_on_sale",
    "journal_id": "depreciation_journal_id",
    "children_ids": "child_ids",
    "asset_lifetime_days": "depreciation_lifetime_days",
    "asset_paused_days": "depreciation_paused_days",
    "depreciation_entries_count": "count_depreciation_posted",
    "total_depreciation_entries_count": "count_depreciation",
    "gross_increase_count": "count_increase",
}
MOVE_FIELDS = {
    "asset_id": "depreciation_asset_id",
    "asset_ids": "capitalised_asset_ids",
    "count_asset": "count_capitalised_asset",
}
MOVE_LINE_FIELDS = {
    "asset_ids": "capitalised_asset_ids",
}
INDEXES = {
    "account_move__asset_id_index": "account_move__depreciation_asset_id_index",
}


def migrate(cr, version):
    if not version:
        return
    for model, renames in (
        ("account.asset", ASSET_FIELDS),
        ("account.move", MOVE_FIELDS),
        ("account.move.line", MOVE_LINE_FIELDS),
    ):
        for old, new in renames.items():
            rename_field(cr, model, old, new)
            rename_in_stored_expressions(cr, old, new, model=model)
    for old, new in INDEXES.items():
        cr.execute(
            SQL(
                "ALTER INDEX IF EXISTS %s RENAME TO %s",
                SQL.identifier(old),
                SQL.identifier(new),
            )
        )
