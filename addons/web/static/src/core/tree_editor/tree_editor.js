import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
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
        defaultConnector: { type: [{ value: "&" }, { value: "|" }], optional: true },
        isSubTree: { type: Boolean, optional: true },
    };
    static defaultProps = {
        defaultConnector: "&",
        readonly: false,
        isSubTree: false,
    };

    setup() {
        this.isTree = isTree;
        this.fieldService = useService("field");
        this.treeProcessor = useService("tree_processor");
        onWillStart(() => this.onPropsUpdated(this.props));
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps));
    }

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

    async prepareInfo(props) {
        const [fieldDefs, getFieldDef] = await Promise.all([
            this.fieldService.loadFields(props.resModel),
            this.treeProcessor.makeGetFieldDef(props.resModel, this.tree),
        ]);
        this.getFieldDef = getFieldDef;
        this.defaultCondition = props.getDefaultCondition(fieldDefs);

        if (props.readonly) {
            this.getConditionDescription = await this.treeProcessor.makeGetConditionDescription(
                props.resModel,
                this.tree
            );
        }
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
            await this.prepareInfo(this.props);
            this.render();
        }
        this.notifyChanges();
    }

    highlightNode(target) {
        const nodeEl = target.closest(".o_tree_editor_node");
        nodeEl.classList.toggle("o_hovered_button");
    }
}
