import { useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ImportAction } from "@base_import/import_action/import_action";
import { BaseImportModel } from "@base_import/import_model";


class AccountLoanImportModel extends BaseImportModel {
    async init() {
        return Promise.resolve();
    }
}


export class AccountLoanImportAction extends ImportAction {
    setup() {
        super.setup();

        this.action = useService("action");

        this.model = useState(new AccountLoanImportModel({
            env: this.env,
            resModel: this.resModel,
            context: this.props.action.params.context || {},
            orm: this.orm,
        }));

        onWillStart(async () => {
            if (this.props.action.params.context) {
                this.model.id = this.props.action.params.context.wizard_id;
                await super.handleFilesUpload([{ name: this.props.action.params.filename }])
            }
        });
    }

    async exit() {
        if (this.model.resModel === "account.loan.line") {
            const action = await this.orm.call("account.loan", "action_file_uploaded", [this.model.context.default_loan_id]);
            return this.action.doAction(action);
        }
        super.exit();
    }
}

registry.category("actions").add("import_loan", AccountLoanImportAction);
