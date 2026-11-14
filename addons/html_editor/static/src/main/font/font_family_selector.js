import { Component, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { PreviewableDropdownItem } from "@html_editor/main/toolbar/previewable_dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownPreview,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class FontFamilySelector extends Component {
    static template = "html_editor.FontFamilySelector";
    static components = { Dropdown, PreviewableDropdownItem };

    props = useProps({
        ...toolbarButtonProps,
        document: t.any().optional(),
        fontFamilyItems: t.array(t.object()),
        currentFontFamily: t.object(),
        focusEditable: t.function(),
        previewableOperation: t.object(),
    });

    fontFamilySelector = signal.ref();

    setup() {
        this.menuRef = signal.ref();
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.fontFamilySelector);
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
