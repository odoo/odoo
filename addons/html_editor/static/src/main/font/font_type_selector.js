import { useState, useRef } from "@web/owl2/utils";
import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { useChildRef } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class FontTypeSelector extends Component {
    static template = "html_editor.FontTypeSelector";
    static props = {
        ...toolbarButtonProps,
        getItems: Function,
        getDisplay: Function,
        onSelected: Function,
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.items = this.props.getItems();
        this.state = useState(this.props.getDisplay());
        this.menuRef = useChildRef();
        this.fontTypeSelector = useRef("fontTypeSelector");
        this.dropdown = useDropdownState();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
        useToolbarDropdownFocus(this.dropdown, this.fontTypeSelector);
    }

    onSelected(item) {
        this.props.onSelected(item);
    }
}
