import { Component, asyncComputed, onWillStart, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { cloneTree, connector, isTree, TRUE_TREE } from "@web/core/tree_editor/condition_tree";
import {
    getDefaultValue,
    getValueEditorInfo,
} from "@web/core/tree_editor/tree_editor_value_editors";
import { getResModel } from "@web/core/tree_editor/utils";
import { areEquivalentTrees } from "@web/core/tree_editor/virtual_operators";
import { useService } from "@web/core/utils/hooks";
import { shallowEqual } from "@web/core/utils/objects";
import { hasTouch } from "@web/core/browser/feature_detection";

export class TreeEditor extends Component {
    static template = "web.TreeEditor";
    static components = {
        Dropdown,
        DropdownItem,
        TreeEditor,
    };
    props = useProps({
        tree: t.object(),
        resModel: t.string(),
        update: t.function(),
        getDefaultCondition: t.function(),
        getPathEditorInfo: t.function(),
        getOperatorEditorInfo: t.function(),
        getDefaultOperator: t.function(),
        readonly: t.boolean().optional(false),
        isDebugMode: t.boolean().optional(),
        defaultConnector: t.selection(["&", "|"]).optional("&"),
        isSubTree: t.boolean().optional(false),
    });

    setup() {
        this.isTree = isTree;
        this.fieldService = useService("field");
        this.treeProcessor = useService("tree_processor");
        this.hasTouch = hasTouch();
        // The normalized tree and the editor info derived from it are resolved
        // together, so a render can never pair one with a stale version of the
        // other (e.g. a tree holding a path that `getFieldDef` doesn't know yet).
        this.info = asyncComputed(() => this.loadInfo());
        onWillStart(async () => {
            await this.info.currentPromise();
        });
    }

    async loadInfo() {
        // Reactive reads have to happen on the synchronous path: anything read
        // after the first `await` is not tracked as a dependency.
        const { defaultConnector, readonly, resModel } = this.props;
        let tree = cloneTree(this.props.tree);
        if (shallowEqual(tree, TRUE_TREE)) {
            tree = connector(defaultConnector);
        } else if (tree.type !== "connector") {
            tree = connector(defaultConnector, [tree]);
        }
        // The local tree can hold state that does not survive a round trip
        // through the parent (virtual operators, in-progress edits), so keep the
        // current object when the incoming one is an equivalent round trip of it.
        if (this.previousTree && areEquivalentTrees(tree, this.previousTree)) {
            tree = this.previousTree;
        }
        this.previousTree = tree;

        const [fieldDefs, getFieldDef] = await Promise.all([
            this.fieldService.loadFields(resModel),
            this.treeProcessor.makeGetFieldDef(resModel, tree),
        ]);
        return {
            tree,
            getFieldDef,
            // Read after an `await` on purpose: function props are reference
            // stable (`.bind` implies `.alike`), and subscribing to them would
            // only add noise.
            defaultCondition: this.props.getDefaultCondition(fieldDefs),
            getConditionDescription: readonly
                ? await this.treeProcessor.makeGetConditionDescription(resModel, tree)
                : null,
        };
    }

    get tree() {
        return this.info()?.tree;
    }

    get defaultCondition() {
        return this.info()?.defaultCondition;
    }

    getFieldDef(path) {
        return this.info()?.getFieldDef(path);
    }

    getConditionDescription(node) {
        return this.info().getConditionDescription(node);
    }

    get className() {
        return `${this.props.readonly ? "o_read_mode" : "o_edit_mode"}`;
    }

    get isDebugMode() {
        return this.props.isDebugMode !== undefined ? this.props.isDebugMode : !!this.env.debug;
    }

    notifyChanges() {
        this.props.update(this.tree);
    }

    _updateConnector(node) {
        node.value = node.value === "&" ? "|" : "&";
        node.negate = false;
    }

    updateConnector(node) {
        this.updateNode(node, () => this._updateConnector(node));
    }

    _updateComplexCondition(node, value) {
        node.value = value;
    }

    updateComplexCondition(node, value) {
        this.updateNode(node, () => this._updateComplexCondition(node, value));
    }

    makeCondition(parent, condition) {
        condition ||= parent.children.findLast((c) => c.type === "condition");
        return cloneTree(condition || this.defaultCondition);
    }

    _addNewCondition(parent, node) {
        if (node) {
            const index = parent.children.indexOf(node);
            parent.children.splice(index + 1, 0, this.makeCondition(parent, node));
        } else {
            parent.children.push(this.makeCondition(parent));
        }
    }

    addNewCondition(parent, node) {
        this.updateNode(parent, () => this._addNewCondition(parent, node));
    }

    _addNewConnector(parent, node) {
        const index = parent.children.indexOf(node);
        const nextConnector = parent.value === "&" ? "|" : "&";
        parent.children.splice(
            index + 1,
            0,
            connector(nextConnector, [this.makeCondition(parent, node)])
        );
    }

    addNewConnector(parent, node) {
        this.updateNode(parent, () => this._addNewConnector(parent, node));
    }

    _delete(ancestors, node) {
        if (ancestors.length === 0) {
            return;
        }
        const parent = ancestors.at(-1);
        const index = parent.children.indexOf(node);
        parent.children.splice(index, 1);
        ancestors = ancestors.slice(0, ancestors.length - 1);
        if (parent.children.length === 0) {
            this._delete(ancestors, parent);
        }
    }

    delete(ancestors, node) {
        const upperNode = ancestors[0] || node;
        this.updateNode(upperNode, () => this._delete(ancestors, node));
    }

    getResModel(node) {
        const fieldDef = this.getFieldDef(node.path);
        const resModel = getResModel(fieldDef);
        return resModel;
    }

    getPathEditorInfo() {
        return this.props.getPathEditorInfo(this.props.resModel, this.defaultCondition);
    }

    getOperatorEditorInfo(node) {
        const fieldDef = this.getFieldDef(node.path);
        return this.props.getOperatorEditorInfo(fieldDef);
    }

    getValueEditorInfo(node) {
        const fieldDef = this.getFieldDef(node.path);
        return getValueEditorInfo(fieldDef, node.operator);
    }

    async _updatePath(node, path) {
        const { fieldDef } = await this.fieldService.loadFieldInfo(this.props.resModel, path);
        node.path = path;
        node.negate = false;
        node.operator = this.props.getDefaultOperator(fieldDef);
        node.value = getDefaultValue(fieldDef, node.operator);
        node.isProperty = fieldDef?.is_property;
    }

    async updatePath(node, path) {
        this.updateNode(node, () => this._updatePath(node, path));
    }

    _updateLeafOperator(node, operator, negate) {
        const fieldDef = this.getFieldDef(node.path);
        node.negate = negate;
        node.operator = operator;
        node.value = getDefaultValue(fieldDef, operator, node.value);
    }

    updateLeafOperator(node, operator, negate) {
        this.updateNode(node, () => this._updateLeafOperator(node, operator, negate));
    }

    _updateLeafValue(node, value) {
        node.value = value;
    }

    updateLeafValue(node, value) {
        this.updateNode(node, () => this._updateLeafValue(node, value));
    }

    async updateNode(node, operation) {
        const previousNode = cloneTree(node);
        await operation();
        if (areEquivalentTrees(node, previousNode)) {
            // no interesting changes for parent
            // this means that the parent might not render the domain selector
            // but we need to udpate editors
            this.info.refresh();
            await this.info.currentPromise();
        }
        this.notifyChanges();
    }

    highlightNode(target) {
        const nodeEl = target.closest(".o_tree_editor_node");
        nodeEl.classList.toggle("o_hovered_button");
    }
}
