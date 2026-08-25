import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { PreviewableDropdownItem } from "@html_editor/main/toolbar/previewable_dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
    useToolbarDropdownPreview,
} from "@html_editor/toolbar_dropdown_hook";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class ImageToolbarDropdown extends Component {
    static components = { Dropdown, PreviewableDropdownItem };
    props = useProps({
        ...toolbarButtonProps,
        name: t.string(),
        icon: t.string().optional(),
        focusEditable: t.function(),
        previewableOperation: t.object(),
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
        this.preview = useToolbarDropdownPreview({
            dropdown: this.dropdown,
            menuRef: this.menuRef,
            previewableOperation: this.props.previewableOperation,
        });
    }

    onSelected(item) {
        this.preview.commit(item);
        this.props.focusEditable();
    }
}
