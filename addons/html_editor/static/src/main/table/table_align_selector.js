import { Component, proxy, signal } from "@odoo/owl";
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

    tableAlignSelectorRef = signal(null);

    setup() {
        this.items = this.props.getItems();
        this.state = proxy(this.props.getDisplay());
        this.menuRef = useChildRef();
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.tableAlignSelectorRef);
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    onSelected(item) {
        this.props.onSelected(item);
        this.props.focusEditable();
    }
}
