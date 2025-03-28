import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { useLoadFieldInfo } from "@web/core/model_field_selector/utils";
import {
    areEquivalentTrees,
    cloneTree,
    condition,
    connector,
    isTree,
} from "@web/core/tree_editor/condition_tree";
import {
    getDefaultValue,
    getValueEditorInfo,
} from "@web/core/tree_editor/tree_editor_value_editors";
import {
    getResModel,
    useMakeGetConditionDescription,
    useMakeGetFieldDef,
} from "@web/core/tree_editor/utils";
import { useService } from "@web/core/utils/hooks";
import { shallowEqual } from "@web/core/utils/objects";

const TRUE_TREE = condition(1, "=", 1);
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
        if (areEquivalentTrees(node, previousNode)) {
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
