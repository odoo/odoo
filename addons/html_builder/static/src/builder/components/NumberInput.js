import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { basicContainerWeWidgetProps, useWeComponent } from "../builder_helpers";

const actionsRegistry = registry.category("website-builder-actions");

export class NumberInput extends Component {
    static template = "html_builder.NumberInput";
    static props = {
        ...basicContainerWeWidgetProps,
        unit: { type: String, optional: true },
    };

    setup() {
        useWeComponent();
        this.state = useState(this.getState());
        this.applyValue = this.env.editor.shared.history.makePreviewableOperation((value) => {
            for (const [actionId, actionParam] of this.getActions()) {
                actionsRegistry.get(actionId).apply({
                    editingElement: this.env.editingElement,
                    param: actionParam,
                    value,
                });
            }
        });
    }
    getState() {
        const [actionId, actionParam] = this.getActions()[0];
        return {
            value: actionsRegistry.get(actionId).getValue({
                editingElement: this.env.editingElement,
                param: actionParam,
            }),
        };
    }
    getActions() {
        const actions = [];
        if (this.props.classAction) {
            actions.push(["classAction", this.props.classAction]);
        }
        if (this.props.attributeAction) {
            actions.push(["attributeAction", this.props.attributeAction]);
        }
        if (this.props.dataAttributeAction) {
            actions.push(["dataAttributeAction", this.props.dataAttributeAction]);
        }
        if (this.props.styleAction) {
            actions.push(["styleAction", this.props.styleAction]);
        }
        if (this.props.action) {
            actions.push([this.props.action, this.props.actionParam]);
        }
        return actions;
    }
    onChange(e) {
        this.applyValue.commit(e.target.value);
    }
    onInput(e) {
        this.applyValue.preview(e.target.value);
    }
}
