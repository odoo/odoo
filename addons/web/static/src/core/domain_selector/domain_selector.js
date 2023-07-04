/** @odoo-module **/

import {
    buildDomain,
    buildDomainSelectorTree,
    cloneTree,
    extractIdsFromDomain,
    extractPathsFromDomain,
    leafToString,
    useGetDefaultLeafDomain,
    useLoadDisplayNames,
} from "@web/core/domain_selector/utils";
import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { getOperatorInfo, toOperator } from "@web/core/domain_selector/domain_selector_operators";
import {
    Editor,
    PathEditor,
    getDefaultOperator,
    getDefaultValue,
    getOperatorsInfo,
    getEditorInfo,
} from "@web/core/domain_selector/domain_selector_fields";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
import { formatValue } from "@web/core/domain_tree";

function collectDifferences(tree, otherTree) {
    // some differences shadow the other differences "below":
    if (tree.type !== otherTree.type) {
        return [{ type: "other" }];
    }
    if (tree.negate !== otherTree.negate) {
        return [{ type: "other" }];
    }
    if (tree.type === "condition") {
        if (formatValue(tree.path) !== formatValue(otherTree.path)) {
            return [{ type: "other" }];
        }
        if (formatValue(tree.value) !== formatValue(otherTree.value)) {
            return [{ type: "other" }];
        }
        if (formatValue(tree.operator) !== formatValue(otherTree.operator)) {
            if (tree.operator === "!=" && otherTree.operator === "set") {
                return [{ type: "replacement", tree, operator: "set" }];
            } else if (tree.operator === "=" && otherTree.operator === "not_set") {
                return [{ type: "replacement", tree, operator: "not_set" }];
            } else {
                return [{ type: "other" }];
            }
        }
        return [];
    }
    if (tree.value !== otherTree.value) {
        return [{ type: "other" }];
    }
    if (tree.children.length !== otherTree.children.length) {
        return [{ type: "other" }];
    }
    const diffs = [];
    for (let i = 0; i < tree.children.length; i++) {
        const child = tree.children[i];
        const otherChild = otherTree.children[i];
        const childDiffs = collectDifferences(child, otherChild);
        if (childDiffs.some((d) => d.type !== "replacement")) {
            return [{ type: "other" }];
        }
        diffs.push(...childDiffs);
    }
    return diffs;
}

function restoreVirtualOperators(tree, otherTree) {
    const diffs = collectDifferences(tree, otherTree);
    // note that the array diffs is homogeneous:
    // we have diffs of the form [], [other], [repl, ..., repl]
    if (diffs.some((d) => d.type !== "replacement")) {
        return;
    }
    for (const { tree, operator } of diffs) {
        tree.operator = operator;
    }
}

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
        this.loadDisplayNames = useLoadDisplayNames();
        this.loadFieldInfo = useLoadFieldInfo();
        this.tree = null;
        this.previousTree = null;
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
            this.previousTree = null;
            return;
        }

        const paths = new Set([
            ...extractPathsFromDomain(domain),
            ...extractPathsFromDomain(defaultLeafDomain),
        ]);

        await this.loadFieldDefs(p.resModel, paths);

        if (p.readonly) {
            const idsByModel = extractIdsFromDomain(domain, this.getFieldDef.bind(this));
            this.displayNames = await this.loadDisplayNames(idsByModel);
        }

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

        if (this.previousTree) {
            // find "first" difference
            restoreVirtualOperators(this.tree, this.previousTree);
            this.previousTree = null;
        }
    }

    notifyChanges() {
        this.previousTree = cloneTree(this.tree);
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

    getDescription(node) {
        const { path, value } = node;
        const fieldDef = this.getFieldDef(path);
        const operatorInfo = this.getOperatorInfo(node);
        return leafToString(fieldDef, operatorInfo, value, this.displayNames[fieldDef?.relation]);
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
            node.operator = getDefaultOperator(fieldDef);
            node.value = getDefaultValue(fieldDef, node.operator);
        }
        this.notifyChanges();
    }

    updateLeafOperator(node, operatorKey) {
        const previousOperatorInfo = getOperatorInfo(node.operator);

        const previousNode = node ? cloneTree(node) : null;

        const [operator, negate] = toOperator(operatorKey);
        node.negate = negate;
        node.operator = operator;

        const editorInfo = this.getEditorInfo(node);
        if (!editorInfo.isSupported(node.value) || editorInfo.shouldResetValue?.(node.value)) {
            node.value = getDefaultValue(this.getFieldDef(node.path), node.operator);
        }

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
                    node.value = getDefaultValue(this.getFieldDef(node.path), node.operator);
                    break;
                }
                // binary operator with a fixed sized array value
                default: {
                    const defaultValue = getDefaultValue(
                        this.getFieldDef(node.path),
                        node.operator
                    );
                    node.value = Array(operatorInfo.valueCount).fill(defaultValue);
                    break;
                }
            }
        }

        if (buildDomain(node) === buildDomain(previousNode)) {
            // no interesting changes for parent (only possible domain formatting/rewriting)
            // this means that parent might not render the domain selector
            // but we need to udpate editors
            this.render();
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
