/** @odoo-module **/

import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { ImportAction } from "@base_import/import_action/import_action";
import { useBankStatementCSVImportModel } from "./bank_statement_csv_import_model";

export class BankStatementImportAction extends ImportAction {
    setup() {
        super.setup();

        this.action = useService("action");

        this.model = useBankStatementCSVImportModel({
            env: this.env,
            resModel: this.resModel,
            context: this.props.action.params.context || {},
            orm: this.orm,
        });

        this.env.config.setDisplayName(_t("Import Bank Statement")); // Displayed in the breadcrumbs
        this.state.filename = this.props.action.params.filename || undefined;

        onWillStart(async () => {
            if (this.props.action.params.context) {
                this.model.id = this.props.action.params.context.wizard_id;
                await super.handleFilesUpload([{ name: this.state.filename }])
            }
        });
    }

    async exit() {
        if (this.model.statement_id) {
            const res = await this.orm.call(
                "account.bank.statement",
                "action_open_bank_reconcile_widget",
                [this.model.statement_id]
            );
            return this.action.doAction(res);
        }
        super.exit();
    }
}

registry.category("actions").add("import_bank_stmt", BankStatementImportAction);
