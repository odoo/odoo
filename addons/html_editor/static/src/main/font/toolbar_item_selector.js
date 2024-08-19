import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class ToolbarItemSelector extends Component {
    static template = "html_editor.ToolbarItemSelector";
    static props = {
        getItems: Function,
        getEditableSelection: Function,
        onSelected: Function,
        getItemFromSelection: Function,
    };
    static defaultProps = {
        isVertical: false,
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.items = this.props.getItems();
        this.state = useState({
            currentItem: this.props.getItemFromSelection(this.props.getEditableSelection()),
        });
        this.isVertical = Boolean(this.state.currentItem.icon);
    }
    onSelected(item) {
        this.state.currentItem = item;
        this.props.onSelected(item);
    }
}
