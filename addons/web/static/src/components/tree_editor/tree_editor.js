// @ts-check

/** @module @web/components/tree_editor/tree_editor - Recursive tree editor component for visually building domain and expression conditions */

/** @import { Condition, Connector, Tree, Value } from "@web/components/tree_editor/condition_tree" */
/** @import { ValueEditorInfo } from "@web/components/tree_editor/tree_editor_value_editors" */
/** @import { OperatorEditorInfo } from "@web/components/tree_editor/tree_editor_operator_editor" */

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import {
    cloneTree,
    connector,
    isTree,
    TRUE_TREE,
} from "@web/components/tree_editor/condition_tree";
import {
    getDefaultValue,
    getValueEditorInfo,
} from "@web/components/tree_editor/tree_editor_value_editors";
import { getResModel } from "@web/components/tree_editor/utils";
import { areEquivalentTrees } from "@web/components/tree_editor/virtual_operators";
import { shallowEqual } from "@web/core/utils/collections/objects";
import { useService } from "@web/core/utils/hooks";
export class TreeEditor extends Component {
    static template = "web.TreeEditor";
    static components = {
        Dropdown,
        DropdownItem,
        TreeEditor,
    };
    static props = {
        tree: Object,
        resModel: String,
        update: Function,
        getDefaultCondition: Function,
        getPathEditorInfo: Function,
        getOperatorEditorInfo: Function,
        getDefaultOperator: Function,
        readonly: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        isDebugMode: { type: Boolean, optional: true },
        defaultConnector: {
            type: [{ value: "&" }, { value: "|" }],
            optional: true,
        },
        isSubTree: { type: Boolean, optional: true },
    };
    static defaultProps = {
        defaultConnector: "&",
        readonly: false,
        isSubTree: false,
    };

    /** Initializes services and lifecycle hooks for tree processing. */
    setup() {
        this.isTree = isTree;
        this.fieldService = useService("field");
        this.treeProcessor = useService("tree_processor");
        onWillStart(() => this.onPropsUpdated(this.props));
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps));
    }

    /**
     * Clones the incoming tree, normalizes it to a connector, and prepares editor info.
     * @param {Object} props
     */
    async onPropsUpdated(props) {
        if (this.tree) {
            this.previousTree = this.tree;
        }
        this.tree = cloneTree(props.tree);
        if (shallowEqual(this.tree, TRUE_TREE)) {
            this.tree = connector(props.defaultConnector);
        } else if (this.tree.type !== "connector") {
            this.tree = connector(props.defaultConnector, [this.tree]);
        }

        if (this.previousTree && areEquivalentTrees(this.tree, this.previousTree)) {
            this.tree = this.previousTree;
            this.previousTree = null;
        }

        await this.prepareInfo(props);
    }

    /**
     * Loads field definitions and builds getFieldDef / condition description helpers.
     * @param {Object} props
     */
    async prepareInfo(props) {
        const [fieldDefs, getFieldDef] = await Promise.all([
            this.fieldService.loadFields(props.resModel),
            this.treeProcessor.makeGetFieldDef(props.resModel, this.tree),
        ]);
        this.getFieldDef = getFieldDef;
        this.defaultCondition = props.getDefaultCondition(fieldDefs);

        if (props.readonly) {
            this.getConditionDescription =
                await this.treeProcessor.makeGetConditionDescription(
                    props.resModel,
                    this.tree,
                );
        }
    }

    /** @returns {string} CSS class based on readonly mode */
    get className() {
        return `${this.props.readonly ? "o_read_mode" : "o_edit_mode"}`;
    }

    /** @returns {boolean} */
    get isDebugMode() {
        return this.props.isDebugMode !== undefined
            ? this.props.isDebugMode
            : !!this.env.debug;
    }

    /** Propagates the current tree state to the parent via the update prop. */
    notifyChanges() {
        this.props.update(this.tree);
    }

    /**
     * Toggles a connector between "&" and "|", resetting negate.
     * @param {Connector} node
     */
    _updateConnector(node) {
        node.value = node.value === "&" ? "|" : "&";
        node.negate = false;
    }

    /**
     * @param {Connector} node
     */
    updateConnector(node) {
        this.updateNode(node, () => this._updateConnector(node));
    }

    /**
     * @param {import("./condition_tree").ComplexCondition} node
     * @param {string} value
     */
    _updateComplexCondition(node, value) {
        node.value = value;
    }

    /**
     * @param {import("./condition_tree").ComplexCondition} node
     * @param {string} value
     */
    updateComplexCondition(node, value) {
        this.updateNode(node, () => this._updateComplexCondition(node, value));
    }

    /**
     * Creates a new condition node, cloning from a reference or the default.
     * @param {Connector} parent
     * @param {Condition} [condition] - reference condition to clone
     * @returns {Tree}
     */
    makeCondition(parent, condition) {
        condition ||= parent.children.findLast((c) => c.type === "condition");
        return cloneTree(condition || this.defaultCondition);
    }

    /**
     * @param {Connector} parent
     * @param {Tree} [node] - sibling to insert after; appends if omitted
     */
    _addNewCondition(parent, node) {
        if (node) {
            const index = parent.children.indexOf(node);
            parent.children.splice(index + 1, 0, this.makeCondition(parent, node));
        } else {
            parent.children.push(this.makeCondition(parent));
        }
    }

    /**
     * @param {Connector} parent
     * @param {Tree} [node]
     */
    addNewCondition(parent, node) {
        this.updateNode(parent, () => this._addNewCondition(parent, node));
    }

    /**
     * Inserts a new sub-connector (with opposite type) after the given node.
     * @param {Connector} parent
     * @param {Tree} node
     */
    _addNewConnector(parent, node) {
        const index = parent.children.indexOf(node);
        const nextConnector = parent.value === "&" ? "|" : "&";
        parent.children.splice(
            index + 1,
            0,
            connector(nextConnector, [this.makeCondition(parent, node)]),
        );
    }

    /**
     * @param {Connector} parent
     * @param {Tree} node
     */
    addNewConnector(parent, node) {
        this.updateNode(parent, () => this._addNewConnector(parent, node));
    }

    /**
     * Removes a node from its parent; recursively removes empty parents.
     * @param {Connector[]} ancestors - parent chain (innermost last)
     * @param {Tree} node
     */
    _delete(ancestors, node) {
        if (ancestors.length === 0) {
            return;
        }
        const parent = ancestors.at(-1);
        const index = parent.children.indexOf(node);
        parent.children.splice(index, 1);
        ancestors = ancestors.slice(0, -1);
        if (parent.children.length === 0) {
            this._delete(ancestors, parent);
        }
    }

    /**
     * @param {Connector[]} ancestors
     * @param {Tree} node
     */
    delete(ancestors, node) {
        const upperNode = ancestors[0] || node;
        this.updateNode(upperNode, () => this._delete(ancestors, node));
    }

    /**
     * @param {Condition} node
     * @returns {string|null} related model name for relational fields
     */
    getResModel(node) {
        const fieldDef = this.getFieldDef(node.path);
        const resModel = getResModel(fieldDef);
        return resModel;
    }

    /** @returns {Object} path editor info for the current model */
    getPathEditorInfo() {
        return this.props.getPathEditorInfo(this.props.resModel, this.defaultCondition);
    }

    /**
     * @param {Condition} node
     * @returns {OperatorEditorInfo}
     */
    getOperatorEditorInfo(node) {
        const fieldDef = this.getFieldDef(node.path);
        return this.props.getOperatorEditorInfo(fieldDef);
    }

    /**
     * @param {Condition} node
     * @returns {ValueEditorInfo}
     */
    getValueEditorInfo(node) {
        const fieldDef = this.getFieldDef(node.path);
        return getValueEditorInfo(fieldDef, node.operator);
    }

    /**
     * Updates a condition's path and resets its operator/value to defaults.
     * @param {Condition} node
     * @param {string} path
     */
    async _updatePath(node, path) {
        const { fieldDef } = await this.fieldService.loadFieldInfo(
            this.props.resModel,
            path,
        );
        node.path = path;
        node.negate = false;
        node.operator = this.props.getDefaultOperator(fieldDef);
        node.value = getDefaultValue(fieldDef, node.operator);
    }

    /**
     * @param {Condition} node
     * @param {string} path
     */
    async updatePath(node, path) {
        this.updateNode(node, () => this._updatePath(node, path));
    }

    /**
     * @param {Condition} node
     * @param {Value} operator
     * @param {boolean} negate
     */
    _updateLeafOperator(node, operator, negate) {
        const fieldDef = this.getFieldDef(node.path);
        node.negate = negate;
        node.operator = operator;
        node.value = getDefaultValue(fieldDef, operator, node.value);
    }

    /**
     * @param {Condition} node
     * @param {Value} operator
     * @param {boolean} negate
     */
    updateLeafOperator(node, operator, negate) {
        this.updateNode(node, () => this._updateLeafOperator(node, operator, negate));
    }

    /**
     * @param {Condition} node
     * @param {any} value
     */
    _updateLeafValue(node, value) {
        node.value = value;
    }

    /**
     * @param {Condition} node
     * @param {any} value
     */
    updateLeafValue(node, value) {
        this.updateNode(node, () => this._updateLeafValue(node, value));
    }

    /**
     * Applies an operation to a node, re-renders if tree is equivalent, and notifies parent.
     * @param {Tree} node
     * @param {() => void|Promise<void>} operation
     */
    async updateNode(node, operation) {
        const previousNode = cloneTree(node);
        await operation();
        if (areEquivalentTrees(node, previousNode)) {
            // no interesting changes for parent
            // this means that the parent might not render the domain selector
            // but we need to udpate editors
            await this.prepareInfo(this.props);
            this.render();
        }
        this.notifyChanges();
    }

    /**
     * Toggles hover highlight on the closest tree editor node element.
     * @param {HTMLElement} target
     */
    highlightNode(target) {
        const nodeEl = target.closest(".o_tree_editor_node");
        nodeEl.classList.toggle("o_hovered_button");
    }
}
