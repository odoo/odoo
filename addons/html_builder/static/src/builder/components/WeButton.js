import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { basicContainerWeWidgetProps, useDomState, useWeComponent } from "../builder_helpers";

const actionsRegistry = registry.category("website-builder-actions");

export class WeButton extends Component {
    static template = "html_builder.WeButton";
    static props = {
        ...basicContainerWeWidgetProps,

        title: { type: String, optional: true },
        label: { type: String, optional: true },
        iconImg: { type: String, optional: true },
        iconImgAlt: { type: String, optional: true },

        actionValue: {
            type: [Boolean, String, Number, { type: Array, element: [Boolean, String, Number] }],
            optional: true,
        },

        // Shorthand actions values.
        classActionValue: { type: [String, Array], optional: true },
        attributeActionValue: { type: [String, Array], optional: true },
        dataAttributeActionValue: { type: [String, Array], optional: true },
        styleActionValue: { type: [String, Array], optional: true },

        slots: { type: Object, optional: true },
    };

    setup() {
        useWeComponent();
        this.state = useDomState(() => ({
            isActive: this.isActive(),
        }));

        if (this.env.buttonGroupBus) {
            useBus(this.env.buttonGroupBus, "BEFORE_CALL_ACTIONS", () => {
                for (const [actionId, actionParam, actionValue] of this.getActions()) {
                    actionsRegistry.get(actionId).clean({
                        editingElement: this.env.editingElement,
                        param: actionParam,
                        value: actionValue,
                    });
                }
            });
        }
        this.call = this.env.editor.shared.history.makePreviewableOperation(
            this.callActions.bind(this)
        );
    }
    callActions() {
        this.env.buttonGroupBus?.trigger("BEFORE_CALL_ACTIONS");
        for (const [actionId, actionParam, actionValue] of this.getActions()) {
            actionsRegistry.get(actionId).apply({
                editingElement: this.env.editingElement,
                param: actionParam,
                value: actionValue,
            });
        }
    }
    getActions() {
        const actions = [];
        if (this.props.classAction) {
            actions.push(["classAction", this.props.classAction, this.props.classActionValue]);
        }
        if (this.props.attributeAction) {
            actions.push([
                "attributeAction",
                this.props.attributeAction,
                this.props.attributeActionValue,
            ]);
        }
        if (this.props.dataAttributeAction) {
            actions.push([
                "dataAttributeAction",
                this.props.dataAttributeAction,
                this.props.dataAttributeActionValue,
            ]);
        }
        if (this.props.styleAction) {
            actions.push(["styleAction", this.props.styleAction, this.props.styleActionValue]);
        }
        if (this.props.action) {
            actions.push([this.props.action, this.props.actionParam, this.props.actionValue]);
        }
        return actions;
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
        return this.getActions().every(([actionId, actionParam, actionValue]) => {
            return actionsRegistry.get(actionId).isActive({
                editingElement: this.env.editingElement,
                param: actionParam,
                value: actionValue,
            });
        });
    }
}
