import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { useDomState } from "../builder_helpers";

const actionsRegistry = registry.category("website-builder-actions");

export class WeButton extends Component {
    static template = "mysterious_egg.WeButton";
    static props = {
        actions: Object,
        title: { type: String, optional: true },
        label: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        iconImgAlt: { type: String, optional: true },
        applyTo: { type: Function, optional: true },
    };

    setup() {
        this.state = useDomState(() => ({
            isActive: this.isActive(),
        }));

        if (this.env.buttonGroupBus) {
            useBus(this.env.buttonGroupBus, "BEFORE_CALL_ACTIONS", () => {
                for (const [actionId, actionParams] of Object.entries(this.props.actions)) {
                    actionsRegistry.get(actionId).clean({
                        editingElement: this.getEditedElement(),
                        params: actionParams,
                    });
                }
            });
        }
        this.call = this.env.editor.shared.makePreviewableOperation(this.callActions.bind(this));
    }
    callActions() {
        this.env.buttonGroupBus?.trigger("BEFORE_CALL_ACTIONS");
        for (const [actionId, actionParams] of Object.entries(this.props.actions)) {
            actionsRegistry.get(actionId).apply({
                editingElement: this.getEditedElement(),
                params: actionParams,
            });
        }
    }
    onClick() {
        this.call.commit();
    }
    onMouseenter() {
        this.call.preview();
    }
    onMouseleave() {
        this.call.revert();
    }
    isActive() {
        return Object.entries(this.props.actions).every(([actionId, actionParams]) => {
            return actionsRegistry.get(actionId).isActive({
                editingElement: this.getEditedElement(),
                params: actionParams,
            });
        });
    }
    getEditedElement() {
        return this.props.applyTo
            ? this.env.editingElement.querySelector(this.props.applyTo)
            : this.env.editingElement;
    }
}
