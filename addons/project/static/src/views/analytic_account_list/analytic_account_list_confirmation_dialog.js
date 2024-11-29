    /** module **/

import { ListConfirmationDialog } from "@web/views/list/list_confirmation_dialog";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";


export class AnalyticAccountListConfirmationDialog extends ListConfirmationDialog {


    static template = "project.AnalyticAccountListView.ConfirmationModal";

    static props = {
        ...super.props,
        accountIdList : Object,
        projectAccountId : Object,
        projectOtherPlan : Object,
    }

    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
         const projects = await this.orm.call("project.project", "get_project_from_account", [this.props.accountIdList]);
         if (projects) {
            if (projects['account_id']) {
                this.props.projectAccountId = projects['account_id'];
            }
            if (projects['other_plan']) {
                this.props.projectOtherPlan = projects['other_plan'];
            }
         }
    }

    async _confirm() {
        await this.orm.call("project.project", "remove_account_from_projects", [this.props.accountIdList]);
        super._confirm()
    }
}
