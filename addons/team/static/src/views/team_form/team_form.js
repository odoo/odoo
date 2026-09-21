/** @odoo-module native */

import { _t } from "@web/core/translation";
import { formView, FormController } from "@web/views/form";
import { registry } from "@web/core/registry";

export class TeamFormController extends FormController {
    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name !== "team_activate_multi_membership") {
            return super.beforeExecuteActionButton(...arguments);
        }
        const record = this.model.root;
        const teamId =
            this.props.resModel === "team.team"
                ? record.resId
                : record.data.team_id?.id;
        const flags = Object.fromEntries(
            Object.entries(record.data).filter(([name]) => name.startsWith("use_")),
        );
        try {
            await this.orm.call(
                "team.team",
                "action_activate_multi_membership",
                [teamId ? [teamId] : []],
                { flags },
            );
        } catch (error) {
            // the button only shows to administrators of the team's usages, so
            // what reaches here is a concurrent update or a failing write, and
            // the server's own message says which
            this.notification.add(
                error.data?.message ||
                    error.message ||
                    _t("An error occurred while activating the Multi-Team option."),
                { type: "danger" },
            );
            return false;
        }
        if (record.isNew || (await record.isDirty())) {
            // the banner is raised by the very edit that is still unsaved:
            // reloading would discard it, and saving first would evict the
            // member from their other team before the option is on
            const changes = { member_warning: false };
            if ("is_membership_multi" in record.fields) {
                changes.is_membership_multi = true;
            }
            await record.update(changes);
        } else {
            await record.load();
        }
        return false;
    }
}

registry.category("views").add("team_form", {
    ...formView,
    Controller: TeamFormController,
});
