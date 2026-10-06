import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class ImageAlignSelector extends Component {
    static template = "html_editor.ImageAlignSelector";
    static components = { Dropdown, DropdownItem };
    props = useProps({
        items: t.array(),
        getDisplay: t.function(),
        focusEditable: t.function(),
        onSelected: t.function(),
        ...toolbarButtonProps,
    });

    imageAlignSelector = signal.ref();

    setup() {
        this.state = proxy(this.props.getDisplay());
        this.menuRef = signal.ref();
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.imageAlignSelector);
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    /**
     * The button is active when the image is not inline (the item without a
     * class).
     */
    get isActive() {
        const inlineItem = this.props.items.find((item) => !item.value);
        return this.state.displayIcon !== inlineItem?.icon;
    }

    onSelected(item) {
        this.props.onSelected(item);
        this.props.focusEditable();
    }
}
