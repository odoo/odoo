import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";

export class FontSelector extends Component {
    static template = "html_editor.FontSelector";
    static props = {
        getItems: Function,
        getDisplay: Function,
        onSelected: Function,
        ...toolbarButtonProps,
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.items = this.props.getItems();
        this.state = useState(this.props.getDisplay());
    }

    onSelected(item) {
        this.props.onSelected(item);
    }
}
