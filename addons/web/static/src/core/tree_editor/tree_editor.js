import {
    getResModel,
    useMakeGetFieldDef,
    useMakeGetConditionDescription,
} from "@web/core/tree_editor/utils";
import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import {
    condition,
    cloneTree,
    formatValue,
    removeVirtualOperators,
    connector,
    isTree,
} from "@web/core/tree_editor/condition_tree";
import {
    getDefaultValue,
    getValueEditorInfo,
} from "@web/core/tree_editor/tree_editor_value_editors";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
import { deepEqual, shallowEqual } from "@web/core/utils/objects";

const TRUE_TREE = condition(1, "=", 1);

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
    if (tree.type === "complex_condition") {
        return [];
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

export class TreeEditor extends Component {
    static template = "web.TreeEditor";
    static components = {
        Dropdown,
        DropdownItem,
        ModelFieldSelector,
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
        this.nameService = useService("name");
        this.loadFieldInfo = useLoadFieldInfo(this.fieldService);
        this.makeGetFieldDef = useMakeGetFieldDef(this.fieldService);
        this.makeGetConditionDescription = useMakeGetConditionDescription(
            this.fieldService,
            this.nameService
        );
        onWillStart(() => this.onPropsUpdated(this.props));
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps));
    }

    async onPropsUpdated(props) {
        this.tree = cloneTree(props.tree);
        if (shallowEqual(this.tree, TRUE_TREE)) {
            this.tree = connector(props.defaultConnector);
        } else if (this.tree.type !== "connector") {
            this.tree = connector(props.defaultConnector, [this.tree]);
        }

        if (this.previousTree) {
            // find "first" difference
            restoreVirtualOperators(this.tree, this.previousTree);
            this.previousTree = null;
        }

        const [fieldDefs, getFieldDef] = await Promise.all([
            this.fieldService.loadFields(props.resModel),
            this.makeGetFieldDef(props.resModel, this.tree),
        ]);
        this.getFieldDef = getFieldDef;
        this.defaultCondition = props.getDefaultCondition(fieldDefs);

        if (props.readonly) {
            this.getConditionDescription = await this.makeGetConditionDescription(
                props.resModel,
                this.tree,
                this.getFieldDef
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
        this.previousTree = cloneTree(this.tree);
        this.props.update(this.tree);
    }

    updateConnector(node, value) {
        node.value = value;
        node.negate = false;
        this.notifyChanges();
    }

    updateComplexCondition(node, value) {
        node.value = value;
        this.notifyChanges();
    }

    createNewLeaf() {
        return cloneTree(this.defaultCondition);
    }

    createNewBranch(value) {
        return connector(value, [this.createNewLeaf(), this.createNewLeaf()]);
    }

    insertRootLeaf(parent) {
        parent.children.push(this.createNewLeaf());
        this.notifyChanges();
    }

    insertLeaf(parent, node) {
        const newNode = node.type !== "connector" ? cloneTree(node) : this.createNewLeaf();
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

    async updatePath(node, path) {
        const { fieldDef } = await this.loadFieldInfo(this.props.resModel, path);
        node.path = path;
        node.negate = false;
        node.operator = this.props.getDefaultOperator(fieldDef);
        node.value = getDefaultValue(fieldDef, node.operator);
        this.notifyChanges();
    }

    updateLeafOperator(node, operator, negate) {
        const previousNode = cloneTree(node);
        const fieldDef = this.getFieldDef(node.path);
        node.negate = negate;
        node.operator = operator;
        node.value = getDefaultValue(fieldDef, operator, node.value);
        if (deepEqual(removeVirtualOperators(node), removeVirtualOperators(previousNode))) {
            // no interesting changes for parent
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

    highlightNode(target) {
        const nodeEl = target.closest(".o_tree_editor_node");
        nodeEl.classList.toggle("o_hovered_button");
    }
}
