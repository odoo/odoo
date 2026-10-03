import { Component, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";

/**
 * Toolbar button opening a menu made of other toolbar items (see `menuId` in
 * toolbar_plugin.js).
 */
export class ToolbarMenu extends Component {
    static template = "html_editor.ToolbarMenu";
    static components = { Dropdown, DropdownItem };
    props = useProps({
        id: t.string(),
        title: t.string(),
        icon: t.string().optional(),
        isActive: t.boolean(),
        isDisabled: t.boolean(),
        items: t.array(),
        getSelection: t.function(),
        onItemSelected: t.function(),
    });

    toggleRef = signal.ref();
    menuRef = signal.ref();

    setup() {
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.toggleRef);
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    onSelected(item) {
        this.props.onItemSelected(item);
    }
}
