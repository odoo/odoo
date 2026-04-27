/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ImportAction } from "@base_import/import_action/import_action";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useAccountMoveLineImportModel } from "./account_import_model";

export class AccountImportAction extends ImportAction {
    setup() {
        super.setup();
        this.actionService = useService("action");

        this.model = useAccountMoveLineImportModel({
            env: this.env,
            resModel: this.resModel,
            context: this.props.action.params.context || {},
            orm: this.orm,
        });
    }

    exit(resIds = null) {
        if (resIds && ["account.move.line", "account.account", "res.partner"].includes(this.resModel)) {
            const names = {
                "account.move.line": _t("Journal Items"),
                "account.account": _t("Chart of Accounts"),
                "res.partner": _t("Customers"),
            }
            const action = {
                name: names[this.resModel],
                res_model: this.resModel,
                type: "ir.actions.act_window",
                views: [[false, "list"], [false, "form"]],
                view_mode: "list",
                domain: [["id", "in", resIds]],
            }
            if (this.resModel == "account.move.line") {
                action.context = { "search_default_posted": 0 };
            }
            return this.actionService.doAction(action);
        }
        super.exit();
    }
};

registry.category("actions").add("account_import_action", AccountImportAction);
