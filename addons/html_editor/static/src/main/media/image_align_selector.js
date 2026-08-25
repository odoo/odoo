import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
    useToolbarDropdownPreview,
} from "@html_editor/toolbar_dropdown_hook";
import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { PreviewableDropdownItem } from "@html_editor/main/toolbar/previewable_dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class ImageAlignSelector extends Component {
    static template = "html_editor.ImageAlignSelector";
    static components = { Dropdown, PreviewableDropdownItem };
    props = useProps({
        items: t.array(),
        getDisplay: t.function(),
        focusEditable: t.function(),
        previewableOperation: t.object(),
        ...toolbarButtonProps,
    });

    imageAlignSelector = signal.ref();

    setup() {
        this.state = proxy(this.props.getDisplay());
        this.menuRef = signal.ref();
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.imageAlignSelector);
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
