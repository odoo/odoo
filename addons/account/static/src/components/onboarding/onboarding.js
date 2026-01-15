import { registry } from "@web/core/registry";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { useService } from "@web/core/utils/hooks";

import { Component } from "@odoo/owl";

class AccountOnboardingWidget extends Component {
    static template = "account.Onboarding";
    static props = {
        ...standardWidgetProps,
    };
    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
    }

    get recordOnboardingSteps() {
        return JSON.parse(this.props.record.data.kanban_dashboard).onboarding?.steps;
    }

    async onboardingLinkClicked(step) {
        const action = await this.orm.call("onboarding.onboarding.step", step.action, [], {
            context: {
                journal_id: this.props.record.resId,
            }
        });
        this.action.doAction(action);
    }
}

export const accountOnboarding = {
    component: AccountOnboardingWidget,
}

registry.category("view_widgets").add("account_onboarding", accountOnboarding);
