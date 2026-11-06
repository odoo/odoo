import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { getToolbarAriaLabel, toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class TableAlignSelector extends Component {
    static template = "html_editor.TableAlignSelector";
    props = useProps({
        getItems: t.function(),
        getDisplay: t.function(),
        onSelected: t.function(),
        focusEditable: t.function(),
        ...toolbarButtonProps,
    });
    static components = { Dropdown, DropdownItem };

    tableAlignSelector = signal.ref();

    setup() {
        this.items = this.props.getItems();
        this.state = proxy(this.props.getDisplay());
        this.menuRef = signal.ref();
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.tableAlignSelector);
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    get ariaLabel() {
        const currentItem = this.items.find((item) => item.mode === this.state.displayName);
        return getToolbarAriaLabel(this.props.title, currentItem?.title);
    }

    onSelected(item) {
        this.props.onSelected(item);
        this.props.focusEditable();
    }
}
