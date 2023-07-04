/** @odoo-module **/

import {
    buildDomain,
    buildDomainSelectorTree,
    cloneTree,
    extractPathsFromDomain,
    useGetDefaultLeafDomain,
} from "@web/core/domain_selector/utils";
import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { getOperatorInfo } from "@web/core/domain_selector/domain_selector_operators";
import {
    Editor,
    PathEditor,
    getDefaultFieldValue,
    getEditorInfo,
    getOperatorsInfo,
} from "@web/core/domain_selector/domain_selector_fields";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
import { Expression } from "@web/core/domain_tree";

export class DomainSelector extends Component {
    static template = "web._DomainSelector";
    static components = {
        Dropdown,
        DropdownItem,
        ModelFieldSelector,
        Editor,
        PathEditor,
    };
    static props = {
        domain: String,
        resModel: String,
        className: { type: String, optional: true },
        defaultConnector: { type: [{ value: "&" }, { value: "|" }], optional: true },
        defaultLeafValue: { type: Array, optional: true },
        isDebugMode: { type: Boolean, optional: true },
        readonly: { type: Boolean, optional: true },
        update: { type: Function, optional: true },
    };
    static defaultProps = {
        className: "",
        defaultConnector: "&",
        isDebugMode: false,
        readonly: true,
        update: () => {},
    };

    setup() {
        this.getDefaultLeafDomain = useGetDefaultLeafDomain();
        this.loadFieldInfo = useLoadFieldInfo();
        this.tree = null;
        onWillStart(() => this.onPropsUpdated(this.props));
        onWillUpdateProps((np) => this.onPropsUpdated(np));
    }

    get className() {
        return `${this.props.readonly ? "o_read_mode" : "o_edit_mode"} ${
            this.props.className
        }`.trim();
    }

    async onPropsUpdated(p) {
        let defaultLeafDomain;
        if (p.defaultLeafValue) {
            try {
                defaultLeafDomain = new Domain([p.defaultLeafValue]);
            } catch {
                // nothing
            }
        }
        if (!defaultLeafDomain) {
            defaultLeafDomain = new Domain(await this.getDefaultLeafDomain(p.resModel));
        }

        let domain;
        let isSupported = true;
        try {
            domain = new Domain(p.domain);
        } catch {
            isSupported = false;
        }

        if (!isSupported) {
            this.tree = null;
            return;
        }

        const paths = new Set([
            ...extractPathsFromDomain(domain),
            ...extractPathsFromDomain(defaultLeafDomain),
        ]);

        await this.loadFieldDefs(p.resModel, paths);

        const options = {
            defaultConnector: p.defaultConnector,
            distributeNot: !p.isDebugMode,
        };
        this.tree = buildDomainSelectorTree(domain, this.getFieldDef.bind(this), options);
        this.defaultCondition = buildDomainSelectorTree(
            defaultLeafDomain,
            this.getFieldDef.bind(this),
            options
        ).children[0];
    }

    notifyChanges() {
        const domain = this.tree ? buildDomain(this.tree) : `[]`;
        this.props.update(domain);
    }

    getFieldDef(path) {
        if (typeof path === "string") {
            return this.fieldDefs[path];
        }
        if ([0, 1].includes(path)) {
            return { type: "integer", string: String(path) };
        }
        return null;
    }

    getDefaultFieldValue(path, operator) {
        return getDefaultFieldValue(this.getFieldDef(path), operator);
    }

    async loadFieldDefs(resModel, paths) {
        const promises = [];
        const fieldDefs = {};
        for (const path of paths) {
            if (typeof path === "string") {
                promises.push(
                    this.loadFieldInfo(resModel, path).then(({ fieldDef }) => {
                        fieldDefs[path] = fieldDef;
                    })
                );
            }
        }
        await Promise.all(promises);
        this.fieldDefs = fieldDefs;
    }

    createNewLeaf() {
        return cloneTree(this.defaultCondition);
    }

    createNewBranch(connector) {
        return {
            type: "connector",
            value: connector,
            negate: false,
            children: [this.createNewLeaf(), this.createNewLeaf()],
        };
    }

    insertRootLeaf(parent) {
        parent.children.push(this.createNewLeaf());
        this.notifyChanges();
    }

    insertLeaf(parent, node) {
        const newNode = node.type === "condition" ? cloneTree(node) : this.createNewLeaf();
        const index = parent.children.indexOf(node);
        parent.children.splice(index + 1, 0, newNode);
        this.notifyChanges();
    }

    insertBranch(parent, node) {
        const nextConnector = parent.value === "&" ? "|" : "&";
        const newNode = this.createNewBranch(nextConnector);
        const index = parent.children.indexOf(node);
        parent.children.splice(index + 1, 0, newNode);
        this.notifyChanges();
    }

    delete(parent, node) {
        const index = parent.children.indexOf(node);
        parent.children.splice(index, 1);
        this.notifyChanges();
    }

    resetDomain() {
        this.tree = buildDomainSelectorTree(new Domain(`[]`));
        this.notifyChanges();
    }

    updateBranchConnector(node, connector) {
        node.value = connector;
        node.negate = false;
        this.notifyChanges();
    }

    updatePath(node, path, { fieldDef } = {}) {
        if (!path) {
            // don't like that
            Object.assign(node, this.createNewLeaf());
        } else {
            node.path = path;
            const operatorInfo = getOperatorsInfo(fieldDef)[0];
            node.operator = operatorInfo.operator;
            node.value = getDefaultFieldValue(fieldDef, node.operator);
        }
        this.notifyChanges();
    }

    updateLeafOperator(node, operator) {
        const previousOperatorInfo = getOperatorInfo(node.operator);
        node.operator = operator;
        const operatorInfo = getOperatorInfo(operator);
        if (previousOperatorInfo.valueCount !== operatorInfo.valueCount) {
            switch (operatorInfo.valueCount) {
                // binary operator with a variable sized array value
                case "variable": {
                    node.value = [];
                    break;
                }
                // unary operator (set | not set)
                case 0: {
                    node.value = false;
                    break;
                }
                // binary operator with a non array value
                case 1: {
                    node.value = this.getDefaultFieldValue(node.path, operator);
                    break;
                }
                // binary operator with a fixed sized array value
                default: {
                    const defaultValue = this.getDefaultFieldValue(node.path, operator);
                    node.value = Array(operatorInfo.valueCount).fill(defaultValue);
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

    isExprValue(value) {
        return value instanceof Expression;
    }

    removeExprValue(node) {
        this.updateLeafValue(node, this.getDefaultFieldValue(node.path, node.operator));
    }

    onDebugValueChange(value) {
        return this.props.update(value, true);
    }

    getEditorInfo(node) {
        return getEditorInfo(this.getFieldDef(node.path), node.operator);
    }

    getOperatorInfo(node) {
        return getOperatorInfo(node.operator, node.negate);
    }

    getOperatorsInfo(node) {
        const fieldDef = this.getFieldDef(node.path);
        const operatorsInfo = getOperatorsInfo(fieldDef);
        if (
            !operatorsInfo.some((op) => op.operator === node.operator && op.negate === node.negate)
        ) {
            const operatorInfo = this.getOperatorInfo(node);
            operatorsInfo.push(operatorInfo);
        }
        return operatorsInfo;
    }

    highlightNode(target, toggle, classNames) {
        const nodeEl = target.closest(".o_domain_node");
        for (const className of classNames.split(/\s+/i)) {
            nodeEl.classList.toggle(className, toggle);
        }
    }
}
