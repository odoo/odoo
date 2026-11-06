import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { getToolbarAriaLabel, toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class ImageToolbarDropdown extends Component {
    static components = { Dropdown, DropdownItem };
    props = useProps({
        ...toolbarButtonProps,
        name: t.string(),
        icon: t.string().optional(),
        focusEditable: t.function(),
        onSelected: t.function(),
        items: t.array(),
        getDisplay: t.function(),
    });
    static template = "html_editor.ImageToolbarDropdown";

    imageToolbarBtn = signal.ref();

    setup() {
        this.items = this.props.items;
        this.state = proxy(this.props.getDisplay());
        this.menuRef = signal.ref();
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.imageToolbarBtn);
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    get ariaLabel() {
        return getToolbarAriaLabel(this.props.title, this.state.displayName);
    }

    onSelected(item) {
        this.props.onSelected(item);
        this.props.focusEditable();
    }
}
