/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";


/**
 * Controller used to directly activate the multi-team option
 * via a button present in the crm team member alert.
 *
 * This alert is only displayed when a user is assigned to
 * multiple teams but the multi-team option is deactivated.
 */
class CrmTeamFormController extends FormController {

    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async beforeExecuteActionButton(clickParams) {
        if (clickParams.name === "crm_team_activate_multi_membership") {
            if (!user.hasGroup("sales_team.group_sale_manager")) {
                return false;
            }
            const alert = document.querySelector(".alert");
            try {
                await this.orm.call("ir.config_parameter", "set_param", [
                    "sales_team.membership_multi",
                    true,
                ]);
                alert?.classList.add('d-none');
            } catch {
                if (alert) {
                    alert.classList.replace("alert-info", "alert-danger");
                    alert.textContent = _t("An error occurred while activating the Multi-Team option.");
                }
            }
            return false;
        }
        return super.beforeExecuteActionButton(...arguments);
    }
}
registry.category("views").add("crm_team_form", {
    ...formView,
    Controller: CrmTeamFormController,
});
