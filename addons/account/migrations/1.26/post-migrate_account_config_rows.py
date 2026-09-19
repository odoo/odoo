from odoo.db.schema import column_exists

COLUMNS = (
    "fiscalyear_last_day",
    "fiscalyear_last_month",
    "fiscalyear_lock_date",
    "tax_lock_date",
    "sale_lock_date",
    "purchase_lock_date",
    "hard_lock_date",
    "transfer_account_id",
    "expects_chart_of_accounts",
    "chart_template",
    "bank_account_code_prefix",
    "cash_account_code_prefix",
    "default_cash_difference_income_account_id",
    "default_cash_difference_expense_account_id",
    "account_journal_suspense_account_id",
    "account_journal_early_pay_discount_gain_account_id",
    "account_journal_early_pay_discount_loss_account_id",
    "transfer_account_code_prefix",
    "account_sale_tax_id",
    "account_purchase_tax_id",
    "account_purchase_receipt_fiscal_position_id",
    "tax_calculation_rounding_method",
    "currency_exchange_journal_id",
    "income_currency_exchange_account_id",
    "expense_currency_exchange_account_id",
    "anglo_saxon_accounting",
    "incoterm_id",
    "qr_code",
    "link_qr_code",
    "display_invoice_amount_total_words",
    "display_invoice_tax_company_currency",
    "account_use_credit_limit",
    "batch_payment_sequence_id",
    "account_opening_move_id",
    "account_opening_date",
    "invoice_terms",
    "terms_type",
    "invoice_terms_html",
    "account_default_pos_receivable_account_id",
    "expense_accrual_account_id",
    "revenue_accrual_account_id",
    "automatic_entry_default_journal_id",
    "account_fiscal_country_id",
    "tax_exigibility",
    "tax_cash_basis_journal_id",
    "account_cash_basis_base_account_id",
    "account_storno",
    "quick_edit_mode",
    "account_discount_income_allocation_id",
    "account_discount_expense_allocation_id",
    "restrictive_audit_trail",
    "autopost_bills",
    "account_price_include",
    "income_account_id",
    "expense_account_id",
    "price_difference_account_id",
    "totals_below_sections",
    "account_return_periodicity",
    "account_return_reminder_day",
    "account_tax_return_journal_id",
    "account_revaluation_journal_id",
    "account_revaluation_expense_provision_account_id",
    "account_revaluation_income_provision_account_id",
    "account_representative_id",
    "account_last_return_cron_refresh",
    "invoicing_switch_threshold",
    "predict_bill_product",
    "sign_invoice",
    "signing_user",
    "deferred_expense_journal_id",
    "deferred_expense_account_id",
    "generate_deferred_expense_entries_method",
    "deferred_expense_amount_computation_method",
    "deferred_revenue_journal_id",
    "deferred_revenue_account_id",
    "generate_deferred_revenue_entries_method",
    "deferred_revenue_amount_computation_method",
)
TRACKED = (
    "fiscalyear_lock_date",
    "tax_lock_date",
    "sale_lock_date",
    "purchase_lock_date",
    "hard_lock_date",
    "restrictive_audit_trail",
)


def migrate(cr, version):
    if not version or not column_exists(cr, "res_company", "chart_template"):
        return
    present = [column for column in COLUMNS if column_exists(cr, "res_company", column)]
    columns = ", ".join(present)
    selected = ", ".join(f"c.{column}" for column in present)
    cr.execute(
        f"""
        INSERT INTO account_config (company_id, {columns},
                                    create_uid, create_date, write_uid, write_date)
             SELECT c.id, {selected}, 1, now() at time zone 'UTC', 1, now() at time zone 'UTC'
               FROM res_company c
              WHERE NOT EXISTS (SELECT 1 FROM account_config ac WHERE ac.company_id = c.id)
        """
    )
    cr.execute(
        f"""
        UPDATE account_config ac
           SET {", ".join(f"{column} = c.{column}" for column in present)}
          FROM res_company c
         WHERE c.id = ac.company_id
        """
    )
    # the lock dates' tracking history follows the data onto the configuration
    cr.execute(
        """
        UPDATE mail_message m
           SET model = 'account.config', res_id = ac.id
          FROM account_config ac
         WHERE m.model = 'res.company'
           AND m.res_id = ac.company_id
           AND EXISTS (
                SELECT 1
                  FROM mail_tracking_value t
                  JOIN ir_model_fields f ON f.id = t.field_id
                 WHERE t.mail_message_id = m.id
                   AND f.model = 'res.company'
                   AND f.name = ANY(%s)
           )
        """,
        [list(TRACKED)],
    )
    cr.execute(
        """
        UPDATE mail_tracking_value t
           SET field_id = new.id
          FROM ir_model_fields old, ir_model_fields new
         WHERE t.field_id = old.id
           AND old.model = 'res.company'
           AND old.name = ANY(%s)
           AND new.model = 'account.config'
           AND new.name = old.name
        """,
        [list(TRACKED)],
    )
