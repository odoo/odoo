/** @odoo-module **/

import { useState } from "@odoo/owl";
import { BaseImportModel } from "@base_import/import_model";

class BankStatementCSVImportModel extends BaseImportModel {
    async init() {
        this.importOptionsValues.bank_stmt_import = {
            value: true,
        };
        return Promise.resolve();
    }

    async _onLoadSuccess(res) {
        super._onLoadSuccess(res);

        if (!res.messages || res.messages.length === 0 || res.messages.length > 1) {
            return;
        }

        const message = res.messages[0];
        if (message.ids) {
            this.statement_line_ids = message.ids
        }

        if (message.messages && message.messages.length > 0) {
            this.statement_id = message.messages[0].statement_id
        }
    }
}

/**
 * @returns {BankStatementCSVImportModel}
 */
export function useBankStatementCSVImportModel({ env, resModel, context, orm }) {
    return useState(new BankStatementCSVImportModel({ env, resModel, context, orm }));
}
