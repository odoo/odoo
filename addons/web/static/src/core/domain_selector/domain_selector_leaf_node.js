/** @odoo-module **/

import { useModelField } from "@web/core/model_field_selector/model_field_hook";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { registry } from "@web/core/registry";
import { DomainSelectorControlPanel } from "./domain_selector_control_panel";

const { Component, onWillStart, onWillUpdateProps, useRef } = owl;

export class DomainSelectorLeafNode extends Component {
    setup() {
        this.root = useRef("root");
        this.modelField = useModelField();
        this.fieldInfo = {
            type: "integer",
            string: "ID",
        };
        onWillStart(async () => {
            this.fieldInfo = await this.loadField(this.props.resModel, this.props.node.operands[0]);
        });
        onWillUpdateProps(async (nextProps) => {
            this.fieldInfo = await this.loadField(nextProps.resModel, nextProps.node.operands[0]);
        });
    }

    get displayedOperator() {
        const op = this.getOperatorInfo(this.props.node.operator);
        return op ? op.label : "?";
    }
    get isValueHidden() {
        const op = this.getOperatorInfo(this.props.node.operator);
        return op ? op.hideValue : false;
    }

    async loadField(resModel, fieldName) {
        const chain = await this.modelField.loadChain(resModel, fieldName);
        if (!chain[chain.length - 1].field && chain.length > 1) {
            return chain[chain.length - 2].field;
        }
        return (
            chain[chain.length - 1].field || {
                type: "integer",
                string: "ID",
            }
        );
    }

    getFieldComponent(type) {
        return registry.category("domain_selector/fields").get(type, null);
    }
    getOperatorInfo(operator) {
        const op = this.getFieldComponent(this.fieldInfo.type)
            .getOperators()
            .find((op) =>
                op.matches({
                    field: this.fieldInfo,
                    operator,
                    value: this.props.node.operands[1],
                })
            );
        if (op) {
            return op;
        }
        return registry
            .category("domain_selector/operator")
            .getAll()
            .find((op) =>
                op.matches({
                    field: this.fieldInfo,
                    operator: this.props.node.operator,
                    value: this.props.node.operands[1],
                })
            );
    }

    async onFieldChange(fieldName) {
        const changes = { fieldName };
        const fieldInfo = await this.loadField(this.props.resModel, fieldName);
        const component = this.getFieldComponent(fieldInfo.type);
        Object.assign(changes, component.onDidTypeChange(fieldInfo));
        this.props.node.update(changes);
    }
    onOperatorChange(ev) {
        const component = this.getFieldComponent(this.fieldInfo.type);
        const operatorInfo = component.getOperators()[parseInt(ev.target.value, 10)];
        const changes = { operator: operatorInfo.value };
        Object.assign(
            changes,
            operatorInfo.onDidChange(this.getOperatorInfo(this.props.node.operator), () =>
                component.onDidTypeChange(this.fieldInfo)
            )
        );
        this.props.node.update(changes);
    }

    onHoverDeleteNodeBtn(hovering) {
        this.root.el.classList.toggle("o_hover_btns", hovering);
    }
    onHoverInsertLeafNodeBtn(hovering) {
        this.root.el.classList.toggle("o_hover_add_node", hovering);
    }
    onHoverInsertBranchNodeBtn(hovering) {
        this.root.el.classList.toggle("o_hover_add_node", hovering);
        this.root.el.classList.toggle("o_hover_add_inset_node", hovering);
    }
}

Object.assign(DomainSelectorLeafNode, {
    template: "web.DomainSelectorLeafNode",
    components: {
        DomainSelectorControlPanel,
        ModelFieldSelector,
    },
});
