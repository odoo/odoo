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
        plan_id : Number
    }

    setup() {
        super.setup();
        this.orm = useService("orm");
        onWillStart(this.onWillStart);
    }

    async onWillStart() {
         const projectsName = await this.orm.call("project.project", "get_projects_name_from_account", [this.props.accountIdList, this.props.plan_id]);
         if (projectsName) {
            if (projectsName['account_id'].length) {
                this.props.projectAccountId = projectsName['account_id'];
            }
            if (projectsName['other_plan'].length) {
                this.props.projectOtherPlan = projectsName['other_plan'];
            }
         }
    }

    async _confirm() {
        await this.orm.call("project.project", "remove_accounts_from_projects", [this.props.accountIdList, this.props.plan_id]);
        super._confirm()
    }
}
