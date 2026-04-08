import { useRef, useState } from "@web/owl2/utils";
import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { useChildRef } from "@web/core/utils/hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class TableAlignSelector extends Component {
    static template = "html_editor.TableAlignSelector";
    static props = {
        getItems: Function,
        getDisplay: Function,
        onSelected: Function,
        focusEditable: Function,
        ...toolbarButtonProps,
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.items = this.props.getItems();
        this.state = useState(this.props.getDisplay());
        this.menuRef = useChildRef();
        this.tableAlignSelector = useRef("tableAlignSelector");
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.tableAlignSelector);
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    onSelected(item) {
        this.props.onSelected(item);
        this.props.focusEditable();
    }
}
