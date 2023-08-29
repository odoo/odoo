/** @odoo-module **/

import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { DomainTreeBuilder } from "@web/core/domain_selector/domain_tree_builder";
import {
    getDefaultFieldValue,
    getEditorInfo,
    getOperatorsInfo,
} from "@web/core/domain_selector/domain_selector_fields";
import { BranchDomainNode } from "@web/core/domain_selector/domain_selector_nodes";
import { findOperator } from "@web/core/domain_selector/domain_selector_operators";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { useService } from "@web/core/utils/hooks";

export class DomainSelector extends Component {
    static template = "web._DomainSelector";
    static components = {
        Dropdown,
        DropdownItem,
        ModelFieldSelector,
    };
    static props = {
        className: { type: String, optional: true },
        resModel: String,
        value: String,
        debugValue: { type: String, optional: true },
        readonly: { type: Boolean, optional: true },
        update: { type: Function, optional: true },
        isDebugMode: { type: Boolean, optional: true },
        defaultLeafValue: { type: Array, optional: true },
    };
    static defaultProps = {
        readonly: true,
        update: () => {},
        isDebugMode: false,
        defaultLeafValue: ["id", "=", 1],
    };

    setup() {
        this.view = useService("view");
        this.treeBuilder = new DomainTreeBuilder();
        this.tree = useState({
            isSupported: false,
            root: null,
        });
        onWillStart(() => this.onPropsUpdated(this.props));
        onWillUpdateProps((np) => this.onPropsUpdated(np));
    }

    async onPropsUpdated(p) {
        try {
            // try to parse and execute the domain, if it fails then the domain is not supported.
            const domain = new Domain(p.value);
            domain.toList();
            this.tree.root = this.treeBuilder.build(
                domain,
                await this.loadFieldDefs(p.resModel, this.extractFieldsFromDomain(domain))
            );
            this.defaultLeaf = this.treeBuilder.build(
                new Domain([p.defaultLeafValue]),
                await this.loadFieldDefs(p.resModel, [p.defaultLeafValue[0]])
            ).children[0];
            this.tree.isSupported = true;
        } catch {
            this.tree.isSupported = false;
            this.tree.root = null;
        }
    }

    extractFieldsFromDomain(domain) {
        const fields = [];
        for (const node of domain.ast.value) {
            if ([4, 10].includes(node.type)) {
                if (node.value[0].type === 1 || [0, 1].includes(node.value[0].value)) {
                    fields.push(node.value[0].value);
                }
            }
        }
        return fields;
    }

    notifyChanges() {
        this.props.update(this.tree.root.toDomain().toString());
    }

    resetDomain() {
        this.props.update("[]");
    }

    async loadFieldDefs(resModel, fields) {
        const promises = [];
        const fieldDefs = {};

        for (const field of fields) {
            promises.push(
                this.loadFieldDef(resModel, field).then((info) => {
                    fieldDefs[field] = info;
                })
            );
        }

        await Promise.all(promises);
        return fieldDefs;
    }

    async loadFieldDef(resModel, field) {
        if ("01".includes(field.toString())) {
            return { type: "integer" };
        }

        const names = field.length ? field.split(".") : [];
        let currentModel = resModel;
        let fieldDef = null;
        for (const name of names) {
            const model = await this.view.loadFields(currentModel);
            fieldDef = model[name];
            currentModel = fieldDef.relation;
        }
        return fieldDef;
    }

    createNewLeaf() {
        return this.defaultLeaf.clone();
    }

    createNewBranch(operator) {
        return new BranchDomainNode(operator, [this.createNewLeaf(), this.createNewLeaf()]);
    }

    insertRootLeaf(parent) {
        parent.add(this.createNewLeaf());
        this.notifyChanges();
    }

    insertLeaf(parent, node) {
        parent.insertAfter(node.id, this.createNewLeaf());
        this.notifyChanges();
    }

    insertBranch(parent, node) {
        const nextOperator = parent.operator === "AND" ? "OR" : "AND";
        parent.insertAfter(node.id, this.createNewBranch(nextOperator));
        this.notifyChanges();
    }

    delete(parent, node) {
        parent.delete(node.id);
        this.notifyChanges();
    }

    updateBranchOperator(node, operator) {
        node.operator = operator;
        this.notifyChanges();
    }

    async updateField(node, field) {
        const fieldDef = await this.loadFieldDef(this.props.resModel, field);
        node.field = { ...fieldDef, name: field };
        node.operator = getOperatorsInfo(fieldDef.type)[0];
        node.value = getDefaultFieldValue(fieldDef);
        this.notifyChanges();
    }

    updateLeafOperator(node, operator) {
        const previousOperator = node.operator;
        node.operator = findOperator(operator);
        if (previousOperator.valueMode !== node.operator.valueMode) {
            switch (node.operator.valueMode) {
                case "none": {
                    node.value = false;
                    break;
                }
                case "multiple": {
                    node.value = previousOperator.valueMode === "none" ? [] : [node.value];
                    break;
                }
                default: {
                    if (previousOperator.valueMode === "none") {
                        node.value = getDefaultFieldValue(node.field);
                    } else {
                        node.value = node.value[0];
                    }
                    break;
                }
            }
        }
        this.notifyChanges();
    }

    updateLeafValue(node, value) {
        node.value = value;
        this.notifyChanges();
    }

    onDebugValueChange(value) {
        return this.props.update(value, true);
    }

    getEditorInfo(node) {
        return getEditorInfo(node.field.type, node.operator.key);
    }

    getOperatorsInfo(node) {
        const operators = getOperatorsInfo(node.field.type);
        if (!operators.some((op) => op.key === node.operator.key)) {
            operators.push(node.operator);
        }
        return operators;
    }

    highlightNode(target, toggle, classNames) {
        const nodeEl = target.closest(".o_domain_node");
        for (const className of classNames.split(/\s+/i)) {
            nodeEl.classList.toggle(className, toggle);
        }
    }
}
