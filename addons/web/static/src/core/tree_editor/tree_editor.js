/** @odoo-module **/

import { Component, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
// import { Editor, PathEditor } from "@web/core/domain_selector/domain_selector_fields";
// import { ModelFieldSelector } from "@web/core/model_field_selector/model_field_selector";
import { Expression } from "@web/core/domain_tree";

function cloneValue(value) {
    if (value instanceof Expression) {
        return new Expression(value.toAST());
    }
    if (Array.isArray(value)) {
        return value.map((val) => cloneValue(val));
    }
    return value;
}

function cloneTree(tree) {
    const clone = {};
    for (const key in tree) {
        clone[key] = cloneValue(tree[key]);
    }
    return clone;
}

export class TreeEditor extends Component {
    static template = "web.TreeEditor";
    static components = {
        Dropdown,
        DropdownItem,
    };
    static props = {
        tree: Object,
        resModel: String,
        update: Function,
        defaultConnector: { type: [{ value: "&" }, { value: "|" }], optional: true },
    };
    static defaultProps = {
        defaultConnector: "&",
    };

    setup() {
        onWillStart(() => this.onPropsUpdated(this.props));
        onWillUpdateProps((nextProps) => this.onPropsUpdated(nextProps));
    }

    onPropsUpdated(props) {
        this.tree = cloneTree(props.tree);
        if (this.tree.type !== "connector") {
            this.tree = { type: "connector", value: props.defaultConnector, children: [this.tree] };
        }
    }

    updateConnector(node, value) {
        node.value = value;
        this.props.update(this.tree);
    }

    updateAtomicCondition(node, value) {
        node.value = value;
        this.props.update(this.tree);
    }
}
