/** @odoo-module **/

import {
    BranchDomainNode,
    DomainValueExpr,
    LeafDomainNode,
} from "@web/core/domain_selector/domain_selector_nodes";
import {
    buildDomain,
    buildDomainSelectorTree,
    extractPathsFromDomain,
    useGetDefaultLeafDomain,
} from "@web/core/domain_selector/utils";
import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { findOperator } from "@web/core/domain_selector/domain_selector_operators";
import {
    Editor,
    getDefaultFieldValue,
    getEditorInfo,
    getOperatorsInfo,
} from "@web/core/domain_selector/domain_selector_fields";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";

export class DomainSelector extends Component {
    static template = "web._DomainSelector";
    static components = {
        Dropdown,
        DropdownItem,
        ModelFieldSelector,
        Editor,
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
        this.tree = { root: null };
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
            this.tree.isSupported = false;
            this.tree.root = buildDomainSelectorTree(new Domain(`[]`), {});
            return;
        }

        const paths = new Set([
            ...extractPathsFromDomain(domain),
            ...extractPathsFromDomain(defaultLeafDomain),
        ]);

        const pathsInfo = await this.loadPathsInfo(p.resModel, paths);

        this.tree.isSupported = true;

        const options = {
            defaultConnector: p.defaultConnector,
            distributeNot: !p.isDebugMode,
            previousTree: this.tree.root,
        };
        this.tree.root = buildDomainSelectorTree(domain, pathsInfo, options);
        this.defaultLeaf = buildDomainSelectorTree(
            defaultLeafDomain,
            pathsInfo,
            options
        ).children[0];
    }

    notifyChanges() {
        this.props.update(buildDomain(this.tree.root));
    }

    async loadPathsInfo(resModel, paths) {
        const promises = [];
        const pathsInfo = {};
        for (const path of paths) {
            promises.push(
                this.loadFieldDef(resModel, path).then((pathInfo) => {
                    pathsInfo[path] = pathInfo;
                })
            );
        }
        await Promise.all(promises);
        return pathsInfo;
    }

    /**
     *
     * @param {string} resModel
     * @param {any} path
     * @returns {Object|null}
     */
    async loadFieldDef(resModel, path) {
        if ([0, 1].includes(path)) {
            return { fieldDef: { type: "integer", string: String(path) }, path };
        }
        const { fieldDef } = await this.loadFieldInfo(resModel, path);
        return { fieldDef, path };
    }

    createNewLeaf() {
        return this.defaultLeaf.clone();
    }

    createNewBranch(connector) {
        return new BranchDomainNode(connector, [this.createNewLeaf(), this.createNewLeaf()]);
    }

    insertRootLeaf(parent) {
        parent.add(this.createNewLeaf());
        this.notifyChanges();
    }

    insertLeaf(parent, node) {
        parent.insertAfter(
            node.id,
            node instanceof LeafDomainNode ? node.clone() : this.createNewLeaf()
        );
        this.notifyChanges();
    }

    insertBranch(parent, node) {
        const nextConnector = parent.connector === "AND" ? "OR" : "AND";
        parent.insertAfter(node.id, this.createNewBranch(nextConnector));
        this.notifyChanges();
    }

    delete(parent, node) {
        parent.delete(node.id);
        this.notifyChanges();
    }

    resetDomain() {
        this.notifyChanges();
    }

    updateBranchConnector(node, connector) {
        node.connector = connector;
        node.negate = false;
        this.notifyChanges();
    }

    async updatePath(node, path, { fieldDef }) {
        const pathInfo = { path, fieldDef };
        node.pathInfo = pathInfo;
        node.operatorInfo = getOperatorsInfo(pathInfo.fieldDef)[0];
        node.value = getDefaultFieldValue(pathInfo.fieldDef);
        this.notifyChanges();
    }

    updateLeafOperator(node, operatorInfo) {
        const previousOperator = node.operatorInfo;
        node.operatorInfo = findOperator(operatorInfo);
        if (previousOperator.valueCount !== node.operatorInfo.valueCount) {
            switch (node.operatorInfo.valueCount) {
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
                    node.value = getDefaultFieldValue(node.pathInfo.fieldDef);
                    break;
                }
                // binary operator with a fixed sized array value
                default: {
                    const defaultValue = getDefaultFieldValue(node.pathInfo.fieldDef);
                    node.value = Array(node.operatorInfo.valueCount).fill(defaultValue);
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
        return value instanceof DomainValueExpr;
    }

    removeExprValue(node) {
        this.updateLeafValue(node, getDefaultFieldValue(node.pathInfo.fieldDef));
    }

    onDebugValueChange(value) {
        return this.props.update(value, true);
    }

    getEditorInfo(node) {
        return getEditorInfo(node.pathInfo.fieldDef, node.operatorInfo.key);
    }

    getOperatorsInfo(node) {
        const operators = getOperatorsInfo(node.pathInfo.fieldDef);
        if (!operators.some((op) => op.key === node.operatorInfo.key)) {
            operators.push(node.operatorInfo);
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
