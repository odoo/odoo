import { Component, useState, useEffect } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

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
        this.dropdown = useDropdownState();
        useEffect(
            (isToolbarVisible) => {
                if (!isToolbarVisible) {
                    this.dropdown.close();
                }
            },
            () => [this.props.isToolbarVisible]
        );
    }

    onSelected(item) {
        this.props.onSelected(item);
    }
}
