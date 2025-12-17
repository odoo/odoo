# Override Map: `account.move`

**Target Model**: `account.move`
**Active Modules**: 25
*(Localization modules `l10n_*` have been excluded)*

## 🔥 Hot Override Points (Global)

Methods overridden by the most modules (Top 15).

| Method | Override Count |
|---|---|
| `_post` | 6 |
| `button_draft` | 6 |
| `button_cancel` | 5 |
| `_reverse_moves` | 3 |
| `_stock_account_get_last_step_stock_moves` | 3 |
| `_get_invoiced_lot_values` | 3 |
| `action_post` | 3 |
| `_invoice_paid_hook` | 2 |
| `_compute_incoterm_location` | 2 |
| `unlink` | 2 |
| `_get_anglo_saxon_price_ctx` | 2 |
| `_compute_debit_count` | 1 |
| `action_view_debit_notes` | 1 |
| `action_debit_note` | 1 |
| `_get_last_sequence_domain` | 1 |

## 🏗️ Core / Functional Overrides
_Modules that implement business logic (Stock, Sales, EDI, etc.)_

### 📦 `account`

- **File**: `../addons/account/models/account_bank_statement_line.py`
  - **Class**: `AccountMove`
  - **Added Fields**: statement_line_ids (_One2many_)
- **File**: `../addons/account/models/account_payment.py`
  - **Class**: `AccountMove`
  - **Added Fields**: payment_ids (_One2many_)
- **File**: `../addons/account/views/account_move_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`view_move_tree_multi_edit`](../addons/account/views/account_move_views.xml#L498) -> `account.view_move_tree`
    - [`view_duplicated_moves_tree_js`](../addons/account/views/account_move_views.xml#L573) -> `account.view_invoice_tree`
    - [`view_out_invoice_tree`](../addons/account/views/account_move_views.xml#L595) -> `account.view_invoice_tree`
    - [`view_out_credit_note_tree`](../addons/account/views/account_move_views.xml#L610) -> `account.view_invoice_tree`
    - [`view_in_invoice_tree`](../addons/account/views/account_move_views.xml#L625) -> `account.view_invoice_tree`
    - [`view_in_invoice_bill_tree`](../addons/account/views/account_move_views.xml#L637) -> `account.view_in_invoice_tree`
    - [`view_in_invoice_refund_tree`](../addons/account/views/account_move_views.xml#L649) -> `account.view_in_invoice_tree`
    - [`view_account_bill_filter`](../addons/account/views/account_move_views.xml#L1733) -> `account.view_account_invoice_filter`
    - [`view_account_move_with_gaps_in_sequence_filter`](../addons/account/views/account_move_views.xml#L1771) -> `account.view_account_invoice_filter`

### 📦 `account_debit_note`

- **File**: `../addons/account_debit_note/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: debit_origin_id (_Many2one_), debit_note_ids (_One2many_), debit_note_count (_Integer_)
  - **Methods**:
    - `_compute_debit_count (@depends)`
    - `action_view_debit_notes`
    - `action_debit_note`
    - `_get_last_sequence_domain`
    - `_get_starting_sequence`
    - `_get_copy_message_content`
- **File**: `../addons/account_debit_note/views/account_move_view.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`view_move_form_debit`](../addons/account_debit_note/views/account_move_view.xml#L3) -> `account.view_move_form`
    - [`view_account_move_filter_debit`](../addons/account_debit_note/views/account_move_view.xml#L28) -> `account.view_account_move_filter`
    - [`view_account_invoice_filter_debit`](../addons/account_debit_note/views/account_move_view.xml#L40) -> `account.view_account_invoice_filter`

### 📦 `account_edi`

- **File**: `../addons/account_edi/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: edi_document_ids (_One2many_), edi_state (_Selection_), edi_error_count (_Integer_), edi_blocking_level (_Selection_), edi_error_message (_Html_), edi_web_services_to_process (_Text_), edi_show_cancel_button (_Boolean_), edi_show_abandon_cancel_button (_Boolean_), edi_show_force_cancel_button (_Boolean_)
  - **Methods**:
    - `_compute_edi_state (@depends)`
    - `_compute_edi_show_force_cancel_button (@depends)`
    - `_compute_edi_error_count (@depends)`
    - `_compute_edi_error_message (@depends)`
    - `_compute_edi_web_services_to_process (@depends)`
    - `_check_edi_documents_for_reset_to_draft`
    - `_compute_show_reset_to_draft_button (@depends)`
    - `_compute_edi_show_cancel_button (@depends)`
    - `_compute_edi_show_abandon_cancel_button (@depends)`
    - `_prepare_edi_tax_details`
    - `_is_ready_to_be_sent`
    - `_post`
    - `button_force_cancel`
    - `button_cancel`
    - `_edi_allow_button_draft`
    - `button_draft`
    - `button_cancel_posted_moves`
    - `button_abandon_cancel_posted_posted_moves`
    - `_get_edi_document`
    - `_get_edi_attachment`
    - `_message_set_main_attachment_id`
    - `button_process_edi_web_services`
    - `action_process_edi_web_services`
    - `_retry_edi_documents_error`
    - `action_retry_edi_documents_error`
    - `_process_attachments_for_template_post`
- **File**: `../addons/account_edi/views/account_move_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`view_out_invoice_tree_inherit`](../addons/account_edi/views/account_move_views.xml#L12) -> `account.view_out_invoice_tree`
    - [`view_out_credit_note_tree_inherit`](../addons/account_edi/views/account_move_views.xml#L29) -> `account.view_out_credit_note_tree`
    - [`view_in_invoice_refund_tree_inherit`](../addons/account_edi/views/account_move_views.xml#L42) -> `account.view_in_invoice_refund_tree`
    - [`view_in_bill_tree_inherit`](../addons/account_edi/views/account_move_views.xml#L55) -> `account.view_in_invoice_bill_tree`
    - [`view_account_invoice_filter`](../addons/account_edi/views/account_move_views.xml#L68) -> `account.view_account_invoice_filter`
    - [`view_move_form_inherit`](../addons/account_edi/views/account_move_views.xml#L83) -> `account.view_move_form`

### 📦 `account_edi_ubl_cii`

- **File**: `../addons/account_edi_ubl_cii/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: ubl_cii_xml_id (_Many2one_), ubl_cii_xml_file (_Binary_), ubl_cii_xml_filename (_Char_)
  - **Methods**:
    - `_compute_filename (@depends)`
    - `action_invoice_download_ubl`
    - `_get_fields_to_detach`
    - `_get_invoice_legal_documents`
    - `get_extra_print_items`
    - `_get_import_file_type`
    - `_unwrap_attachment`
    - `_ubl_parse_attached_document (@model)`
    - `_get_edi_decoder`
    - `_need_ubl_cii_xml`
    - `_is_exportable_as_self_invoice`
    - `_get_line_vals_list (@model)`
    - `_get_specific_tax`

### 📦 `account_fleet`

- **File**: `../addons/account_fleet/models/account_move.py`
  - **Class**: `AccountMove`
  - **Methods**: `_post`
- **File**: `../addons/account_fleet/views/account_move_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`view_move_form`](../addons/account_fleet/views/account_move_views.xml#L4) -> `account.view_move_form`
    - [`account_move_view_tree`](../addons/account_fleet/views/account_move_views.xml#L20) -> `account.view_move_tree`

### 📦 `account_payment`

- **File**: `../addons/account_payment/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: transaction_ids (_Many2many_), authorized_transaction_ids (_Many2many_), transaction_count (_Integer_), amount_paid (_Monetary_)
  - **Methods**:
    - `_compute_authorized_transaction_ids (@depends)`
    - `_compute_transaction_count (@depends)`
    - `_compute_amount_paid (@depends)`
    - `_has_to_be_paid`
    - `_get_online_payment_error`
    - `get_portal_last_transaction (@private)`
    - `payment_action_capture`
    - `payment_action_void`
    - `action_view_payment_transactions`
    - `_get_default_payment_link_values`
    - `_generate_portal_payment_qr`
    - `_get_portal_payment_link`
- **File**: `../addons/account_payment/views/account_move_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`account_invoice_view_form_inherit_payment`](../addons/account_payment/views/account_move_views.xml#L4) -> `account.view_move_form`

### 📦 `account_peppol`

- **File**: `../addons/account_peppol/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: peppol_message_uuid (_Char_), peppol_move_state (_Selection_)
  - **Methods**:
    - `action_send_and_print`
    - `action_cancel_peppol_documents`
    - `_compute_display_send_button`
    - `_compute_peppol_move_state (@depends)`
    - `_notify_by_email_prepare_rendering_context`
- **File**: `../addons/account_peppol/views/account_move_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`account_peppol_view_move_form`](../addons/account_peppol/views/account_move_views.xml#L3) -> `account.view_move_form`
    - [`account_peppol_view_out_invoice_tree_inherit`](../addons/account_peppol/views/account_move_views.xml#L24) -> `account.view_out_invoice_tree`
    - [`account_peppol_view_out_credit_note_tree_inherit`](../addons/account_peppol/views/account_move_views.xml#L35) -> `account.view_out_credit_note_tree`
    - [`account_peppol_view_account_invoice_filter`](../addons/account_peppol/views/account_move_views.xml#L46) -> `account.view_account_invoice_filter`

### 📦 `account_peppol_advanced_fields`

- **File**: `../addons/account_peppol_advanced_fields/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: peppol_contract_document_reference (_Char_), peppol_project_reference (_Char_), peppol_originator_document_reference (_Char_), peppol_despatch_document_reference (_Char_), peppol_additional_document_reference (_Char_), peppol_accounting_cost (_Char_), peppol_delivery_location_id (_Char_)
- **File**: `../addons/account_peppol_advanced_fields/views/account_move_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`view_move_form_inherit_peppol`](../addons/account_peppol_advanced_fields/views/account_move_views.xml#L4) -> `account.view_move_form`

### 📦 `event_booth_sale`

- **File**: `../addons/event_booth_sale/models/account_move.py`
  - **Class**: `AccountMove`
  - **Methods**: `_invoice_paid_hook`

### 📦 `hr_expense`

- **File**: `../addons/hr_expense/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: expense_ids (_One2many_), nb_expenses (_Integer_)
  - **Methods**:
    - `_compute_nb_expenses`
    - `_compute_commercial_partner_id (@depends)`
    - `_check_expense_ids (@constrains)`
    - `action_open_expense`
    - `_check_journal_move_type`
    - `_creation_message`
    - `_compute_needed_terms (@depends)`
    - `_prepare_product_base_line_for_taxes_computation`
    - `_reverse_moves`
    - `button_cancel`
- **File**: `../addons/hr_expense/views/account_move_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`view_move_form_inherit_expense`](../addons/hr_expense/views/account_move_views.xml#L4) -> `account.view_move_form`

### 📦 `mrp_account`

- **File**: `../addons/mrp_account/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: wip_production_ids (_Many2many_), wip_production_count (_Integer_)
  - **Methods**:
    - `copy`
    - `_compute_wip_production_count (@depends)`
    - `action_view_wip_production`
- **File**: `../addons/mrp_account/views/account_move_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`view_move_form_inherit_mrp_account`](../addons/mrp_account/views/account_move_views.xml#L2) -> `account.view_move_form`

### 📦 `point_of_sale`

- **File**: `../addons/point_of_sale/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: pos_order_ids (_One2many_), pos_payment_ids (_One2many_), pos_refunded_invoice_ids (_Many2many_), reversed_pos_order_id (_Many2one_), pos_session_ids (_One2many_), pos_order_count (_Integer_)
  - **Methods**:
    - `_compute_origin_pos_count (@depends)`
    - `_compute_always_tax_exigible (@depends)`
    - `_stock_account_get_last_step_stock_moves`
    - `_get_invoiced_lot_values`
    - `_compute_payments_widget_reconciled_info`
    - `_compute_amount`
    - `_compute_tax_totals`
    - `_compute_is_storno`
    - `action_view_source_pos_orders`
    - `button_draft`
    - `_load_pos_data_fields (@model)`
- **File**: `../addons/point_of_sale/views/account_move_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`view_account_journal_pos_user_form`](../addons/point_of_sale/views/account_move_views.xml#L3) -> `account.view_move_form`

### 📦 `pos_sale`

- **File**: `../addons/pos_sale/models/account_move.py`
  - **Class**: `AccountMove`
  - **Methods**: `reflect_cancelled_sol`, `button_cancel`, `action_post`

### 📦 `product_email_template`

- **File**: `../addons/product_email_template/models/account_move.py`
  - **Class**: `AccountMove`
  - **Methods**: `invoice_validate_send_email`, `_post`

### 📦 `purchase`

- **File**: `../addons/purchase/models/account_invoice.py`
  - **Class**: `AccountMove`
  - **Added Fields**: purchase_vendor_bill_id (_Many2one_), purchase_id (_Many2one_), purchase_order_count (_Integer_), purchase_order_name (_Char_), is_purchase_matched (_Boolean_), purchase_warning_text (_Text_)
  - **Methods**:
    - `_onchange_purchase_auto_complete (@onchange)`
    - `_onchange_partner_id (@onchange)`
    - `_compute_is_purchase_matched (@depends)`
    - `_compute_origin_po_count (@depends)`
    - `_compute_purchase_order_name (@depends)`
    - `_compute_purchase_warning_text (@depends)`
    - `action_purchase_matching`
    - `action_view_source_purchase_orders`
    - `create (@model_create_multi)`
    - `write`
    - `_add_purchase_order_lines`
    - `_find_matching_subset_po_lines`
    - `_find_matching_po_and_inv_lines`
    - `_set_purchase_orders`
    - `_match_purchase_orders`
    - `_find_and_set_purchase_orders`
- **File**: `../addons/purchase/views/account_move_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`view_move_form_inherit_purchase`](../addons/purchase/views/account_move_views.xml#L3) -> `account.view_move_form`

### 📦 `purchase_stock`

- **File**: `../addons/purchase_stock/models/account_invoice.py`
  - **Class**: `AccountMove`
  - **Methods**:
    - `_stock_account_prepare_anglo_saxon_in_lines_vals`
    - `button_draft`
    - `_post`
    - `_stock_account_get_last_step_stock_moves`
    - `_compute_incoterm_location (@depends)`

### 📦 `sale`

- **File**: `../addons/sale/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: team_id (_Many2one_), campaign_id (_Many2one_), medium_id (_Many2one_), source_id (_Many2one_), sale_order_count (_Integer_), sale_warning_text (_Text_)
  - **Methods**:
    - `unlink`
    - `_compute_team_id (@depends)`
    - `_compute_origin_so_count (@depends)`
    - `_compute_sale_warning_text (@depends)`
    - `_reverse_moves`
    - `action_post`
    - `button_draft`
    - `button_cancel`
    - `_post`
    - `_invoice_paid_hook`
    - `_action_invoice_ready_to_be_sent`
    - `action_view_source_sale_orders`
    - `_is_downpayment`
    - `_get_sale_order_invoiced_amount`
    - `_get_partner_credit_warning_exclude_amount`
- **File**: `../addons/sale/views/account_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`account_invoice_groupby_inherit`](../addons/sale/views/account_views.xml#L4) -> `account.view_account_invoice_filter`
    - [`account_invoice_view_tree`](../addons/sale/views/account_views.xml#L18) -> `account.view_invoice_tree`
    - [`account_invoice_form`](../addons/sale/views/account_views.xml#L29) -> `account.view_move_form`

### 📦 `sale_expense`

- **File**: `../addons/sale_expense/models/account_move.py`
  - **Class**: `AccountMove`
  - **Methods**: `_reverse_moves`, `button_draft`, `unlink`

### 📦 `sale_project`

- **File**: `../addons/sale_project/models/account_move.py`
  - **Class**: `AccountMove`
  - **Methods**: `_get_action_per_item`

### 📦 `sale_stock`

- **File**: `../addons/sale_stock/models/account_move.py`
  - **Class**: `AccountMove`
  - **Methods**:
    - `_stock_account_get_last_step_stock_moves`
    - `_get_invoiced_lot_values`
    - `_compute_delivery_date (@depends)`
    - `_compute_incoterm_location (@depends)`
    - `_get_anglo_saxon_price_ctx`
    - `_get_protected_vals`

### 📦 `sale_timesheet`

- **File**: `../addons/sale_timesheet/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: timesheet_ids (_One2many_), timesheet_count (_Integer_), timesheet_encode_uom_id (_Many2one_), timesheet_total_duration (_Integer_)
  - **Methods**:
    - `_compute_timesheet_total_duration (@depends)`
    - `_compute_timesheet_count (@depends)`
    - `action_view_timesheet`
    - `_link_timesheets_to_invoice`
    - `_get_range_dates`
    - `action_post`
- **File**: `../addons/sale_timesheet/views/account_invoice_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`account_invoice_view_form_inherit_sale_timesheet`](../addons/sale_timesheet/views/account_invoice_views.xml#L60) -> `account.view_move_form`

### 📦 `snailmail_account`

- **File**: `../addons/snailmail_account/models/account_move.py`
  - **Class**: `AccountMove`
  - **Methods**:
    - `unlink_snailmail_letters (@ondelete)`

### 📦 `stock_account`

- **File**: `../addons/stock_account/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: stock_move_ids (_One2many_)
  - **Methods**:
    - `_get_lines_onchange_currency`
    - `copy_data`
    - `_post`
    - `button_draft`
    - `button_cancel`
    - `_stock_account_prepare_realtime_out_lines_vals`
    - `_get_anglo_saxon_price_ctx`
    - `_get_related_stock_moves`
    - `_get_invoiced_lot_values`

### 📦 `stock_landed_costs`

- **File**: `../addons/stock_landed_costs/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: landed_costs_ids (_One2many_), landed_costs_visible (_Boolean_)
  - **Methods**:
    - `_compute_landed_costs_visible (@depends)`
    - `button_create_landed_costs`
    - `action_view_landed_costs`
    - `_update_order_line_info`
- **File**: `../addons/stock_landed_costs/views/account_move_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`account_view_move_form_inherited`](../addons/stock_landed_costs/views/account_move_views.xml#L3) -> `account.view_move_form`

### 📦 `website_sale`

- **File**: `../addons/website_sale/models/account_move.py`
  - **Class**: `AccountMove`
  - **Added Fields**: website_id (_Many2one_)
  - **Methods**:
    - `_auto_init`
    - `preview_invoice`
    - `_compute_website_id (@depends)`
- **File**: `../addons/website_sale/views/account_move_views.xml`
  - **Class**: `XML View Override`
  - **Modified Views**:
    - [`account_move_view_form`](../addons/website_sale/views/account_move_views.xml#L4) -> `account.view_move_form`

