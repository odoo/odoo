import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { useDomState } from "../builder_helpers";

const actionsRegistry = registry.category("website-builder-actions");

export class Button extends Component {
    static template = "mysterious_egg.Button";
    static props = {
        id: { type: String, optional: true },
        label: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        iconImgAlt: { type: String, optional: true },
        actions: { type: Object, optional: true },
        isActive: { type: Function, optional: true },
        onClick: { type: Function, optional: true },
        applyTo: { type: Function, optional: true },
    };

    setup() {
        this.state = useDomState(() => ({
            isActive: this.isActive(),
        }));

        if (this.env.buttonGroupBus) {
            useBus(this.env.buttonGroupBus, "BEFORE_CALL_ACTIONS", () => {
                if (!this.props.actions) {
                    return;
                }
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
        if (!this.props.actions) {
            return;
        }
        for (const [actionId, actionParams] of Object.entries(this.props.actions)) {
            actionsRegistry.get(actionId).onButtonClicked({
                editingElement: this.getEditedElement(),
                params: actionParams,
            });
        }
    }
    onClick() {
        this.props.onClick ? this.props.onClick() : this.call.commit();
    }
    onMouseenter() {
        if (!this.props.actions) {
            return;
        }
        this.call.preview();
    }
    onMouseleave() {
        if (!this.props.actions) {
            return;
        }
        this.call.revert();
    }
    isActive() {
        if (this.props.isActive) {
            return this.props.isActive();
        }
        return this.props.actions
            ? Object.entries(this.props.actions).every(([actionId, actionParams]) => {
                  return actionsRegistry.get(actionId).isButtonActive({
                      editingElement: this.getEditedElement(),
                      params: actionParams,
                  });
              })
            : false;
    }
    getEditedElement() {
        return this.props.applyTo
            ? this.env.editingElement.querySelector(this.props.applyTo)
            : this.env.editingElement;
    }
}
