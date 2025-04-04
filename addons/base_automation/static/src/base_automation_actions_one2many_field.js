import { Component, useExternalListener, useEffect, useRef } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useThrottleForAnimation } from "@web/core/utils/timing";

class ActionsOne2ManyField extends Component {
    static props = ["*"];
    static template = "base_automation.ActionsOne2ManyField";
    setup() {
        this.root = useRef("root");

        let adaptCounter = 0;
        useEffect(
            () => {
                this.adapt();
            },
            () => [adaptCounter]
        );
        const throttledRenderAndAdapt = useThrottleForAnimation(() => {
            adaptCounter++;
            this.render();
        });
        useExternalListener(window, "resize", throttledRenderAndAdapt);
        this.currentActions = this.props.record.data[this.props.name].records;
        this.hiddenActionsCount = 0;
    }
    async adapt() {
        // --- Initialize ---
        // use getBoundingClientRect to get unrounded width
        // of the elements in order to avoid rounding issues
        const rootWidth = this.root.el.getBoundingClientRect().width;

        // remove all d-none classes (needed to get the real width of the elements)
        const actionsEls = Array.from(this.root.el.children).filter((el) => el.dataset.actionId);
        actionsEls.forEach((el) => el.classList.remove("d-none"));
        const actionsTotalWidth = actionsEls.reduce(
            (sum, el) => sum + el.getBoundingClientRect().width,
            0
        );

        // --- Check first overflowing action ---
        let overflowingActionId;
        if (actionsTotalWidth > rootWidth) {
            let width = 56; // for the ellipsis
            for (const el of actionsEls) {
                const elWidth = el.getBoundingClientRect().width;
                if (width + elWidth > rootWidth) {
                    // All the remaining elements are overflowing
                    overflowingActionId = el.dataset.actionId;
                    const firstOverflowingEl = actionsEls.find(
                        (el) => el.dataset.actionId === overflowingActionId
                    );
                    const firstOverflowingIndex = actionsEls.indexOf(firstOverflowingEl);
                    const overflowingEls = actionsEls.slice(firstOverflowingIndex);
                    // hide overflowing elements
                    overflowingEls.forEach((el) => el.classList.add("d-none"));
                    break;
                }
                width += elWidth;
            }
        }

        // --- Final rendering ---
        const initialHiddenActionsCount = this.hiddenActionsCount;
        this.hiddenActionsCount = overflowingActionId
            ? this.currentActions.length -
              this.currentActions.findIndex((action) => action.id === overflowingActionId)
            : 0;
        if (initialHiddenActionsCount !== this.hiddenActionsCount) {
            // Render only if hidden actions count has changed.
            return this.render();
        }
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

registry.category("fields").add("base_automation_actions_one2many", actionsOne2ManyField);
