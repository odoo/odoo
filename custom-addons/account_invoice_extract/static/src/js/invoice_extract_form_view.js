/** @odoo-module **/

import { registry } from "@web/core/registry";
import { AccountMoveFormView } from '@account/components/account_move_form/account_move_form';
import { InvoiceExtractFormRenderer } from '@account_invoice_extract/js/invoice_extract_form_renderer';

const AccountMoveFormViewExtract = {
    ...AccountMoveFormView,
    Renderer: InvoiceExtractFormRenderer,
};

registry.category("views").add("account_move_form", AccountMoveFormViewExtract, { force: true });
