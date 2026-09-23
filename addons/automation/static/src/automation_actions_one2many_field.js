/** @odoo-module native */
import { Component, useExternalListener, useEffect, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/translation";
import { registry } from "@web/core/registry";
import { useThrottleForAnimation } from "@web/core/utils/timing";

class ActionsOne2ManyField extends Component {
    static props = ["*"];
    static template = "automation.ActionsOne2ManyField";
    setup() {
        this.root = useRef("root");

        this.state = useState({ hiddenActionsCount: 0 });
        useEffect(
            () => {
                this.adapt();
            },
            () => [],
        );
        useExternalListener(
            window,
            "resize",
            useThrottleForAnimation(() => this.adapt()),
        );
        this.currentActions = this.props.record.data[this.props.name].records;
    }
    get hiddenActionsCount() {
        return this.state.hiddenActionsCount;
    }
    adapt() {
        const rootWidth = this.root.el.getBoundingClientRect().width;

        const actionsEls = Array.from(this.root.el.children).filter(
            (el) => el.dataset.actionId,
        );
        actionsEls.forEach((el) => el.classList.remove("d-none"));
        const actionsTotalWidth = actionsEls.reduce(
            (sum, el) => sum + el.getBoundingClientRect().width,
            0,
        );

        let overflowingActionId;
        if (actionsTotalWidth > rootWidth) {
            let width = 56;
            for (const el of actionsEls) {
                const elWidth = el.getBoundingClientRect().width;
                if (width + elWidth > rootWidth) {
                    overflowingActionId = el.dataset.actionId;
                    const firstOverflowingEl = actionsEls.find(
                        (el) => el.dataset.actionId === overflowingActionId,
                    );
                    const firstOverflowingIndex =
                        actionsEls.indexOf(firstOverflowingEl);
                    const overflowingEls = actionsEls.slice(firstOverflowingIndex);
                    overflowingEls.forEach((el) => el.classList.add("d-none"));
                    break;
                }
                width += elWidth;
            }
        }

        this.state.hiddenActionsCount = overflowingActionId
            ? this.currentActions.length -
              this.currentActions.findIndex(
                  (action) => action.id === overflowingActionId,
              )
            : 0;
    }
    get moreText() {
        const isPlural = this.hiddenActionsCount > 1;
        return isPlural ? _t("%s actions", this.hiddenActionsCount) : _t("1 action");
    }
}

const actionsOne2ManyField = {
    component: ActionsOne2ManyField,
    relatedFields: [
        { name: "name", type: "char" },
        { name: "state", type: "selection" },
    ],
};

registry.category("fields").add("automation_actions_one2many", actionsOne2ManyField);
