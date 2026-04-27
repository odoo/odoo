/** @odoo-module **/

import { BaseImportModel } from "@base_import/import_model";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(BaseImportModel.prototype, {
    async init() {
        await super.init(...arguments);

        if (this.resModel === "account.bank.statement") {
            this.importTemplates.push({
                label: _t("Import Template for Bank Statements"),
                template: "/account_bank_statement_import/static/csv/account.bank.statement.csv",
            });
        }
    }
});
