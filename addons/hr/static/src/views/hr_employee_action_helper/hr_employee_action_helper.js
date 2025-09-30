import { ActionHelper } from "@web/views/action_helper";
import { user } from "@web/core/user";
import { onWillStart, proxy, Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

class OnboardingIconCard extends Component {
    static template = "hr.OnboardingIconCard";
    static props = {
        label: { type: String },
        iconPath: { type: String },
    };
}

class OnboardingHelperBlocks extends Component {
    static template = "hr.OnboardingHelperBlocks";
    static components = { OnboardingIconCard };
    static props = {};
}

export class HrEmployeeActionHelper extends ActionHelper {
    static template = "hr.EmployeeActionHelper";
    static components = { OnboardingHelperBlocks };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = proxy({ isOnboarding: null });
        onWillStart(async () => {
            this.state.isOnboarding = await this.orm.call("hr.employee", "is_onboarding", [
                user.activeCompanies.map((company) => company.id),
            ]);
        });
    }

    get showDefaultHelper() {
        return !this.showOnboardingHelper && super.showDefaultHelper;
    }

    get showOnboardingHelper() {
        // If on mobile and that the user hasn't the employee rights, then keep the same behavior as
        // the ActionHelper (because no onboarding helper really suit this case)
        return this.state.isOnboarding && !this.env.isSmall;
    }

    async loadDemoData() {
        await this.orm.call("hr.employee", "load_demo_data", []);
        await this.env.model.load();
    }

    loadNewEmployeeForm() {
        this.action.doAction({
            name: _t("Employees"),
            res_model: "hr.employee",
            type: "ir.actions.act_window",
            views: [[false, "form"]],
            view_mode: "form",
            target: "current",
        });
    }
}
