/** @odoo-module */

import { registry } from "@web/core/registry";
import { UpdateIncludedPdfDialog } from "@sale_pdf_quote_builder/js/update_included_pdf/update_included_pdf";

async function actionSaleUpdateIncludedPdf(env, action) {
    env.services.dialog.add(UpdateIncludedPdfDialog, action.params);
}

registry
    .category("actions")
    .add("actionSaleUpdateIncludedPdf", actionSaleUpdateIncludedPdf);
