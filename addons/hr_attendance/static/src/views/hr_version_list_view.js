import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";
import { _t } from "@web/core/l10n/translation";


export class VersionOvertimeRulesetListController extends ListController {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
    }
    async onAdd() {
        const records = this.model.root.selection;
        if (records && records.some((record) => record.data.has_ruleset_id)) {
            this.dialogService.add(ConfirmationDialog, {
                body: _t("One or more selected records already have a ruleset assigned (highlighted in yellow). Do you want to overwrite them?"),
                confirmLabel: _t("Overwrite"),
                confirm: async () => {
                    return this.assignRuleset();
                },
                cancel: () => { },
            });
        } else {
            return this.assignRuleset();
        }
    }
    async assignRuleset() {
        await this.orm.call(
            "hr.version",
            "action_assign_ruleset",
            [this.model.root.selection.map((record) => record.resId)],
            { context: { default_ruleset_id: this.props.context.default_ruleset_id } }
        );
        await this.actionService.doAction({ type: 'ir.actions.act_window_close' });
    }
}

export const versionOvertimeRulesetListView = {
    ...listView,
    buttonTemplate: 'hr_attendance.AssignVersionToRuleset.buttons',
    Controller: VersionOvertimeRulesetListController,
};

registry.category("views").add("version_overtime_ruleset_list_view", versionOvertimeRulesetListView)
