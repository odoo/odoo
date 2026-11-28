import { Component, computed, proxy, signal, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
import { PreviewableDropdownItem } from "@html_editor/main/toolbar/previewable_dropdown_item";
import { getToolbarAriaLabel, toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useFocusTooltip,
    useToolbarDropdownFocus,
    useToolbarDropdownPreview,
} from "@html_editor/toolbar_dropdown_hook";

export class TableBorderStyleSelector extends Component {
    static template = "html_editor.TableBorderStyleSelector";
    props = useProps({
        getItems: t.function(),
        getDisplay: t.function(),
        previewableOperation: t.object(),
        ...toolbarButtonProps,
    });
    static components = { Dropdown, PreviewableDropdownItem };

    buttonRef = signal.ref();

    setup() {
        this.items = this.props.getItems();
        this.state = proxy(this.props.getDisplay());
        this.menuRef = signal.ref();
        this.dropdown = useDropdownState();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
        this.preview = useToolbarDropdownPreview({
            dropdown: this.dropdown,
            menuRef: this.menuRef,
            previewableOperation: this.props.previewableOperation,
        });
        useFocusTooltip(this.menuRef);
        useToolbarDropdownFocus(this.dropdown, this.buttonRef, this.menuRef);
    }

    ariaLabel = computed(() => {
        const value =
            this.state.displayName === "none"
                ? _t("None")
                : this.items.find((item) => item.value === this.state.displayName)?.title;
        return getToolbarAriaLabel(this.props.title, value);
    });

    onSelected(item) {
        this.preview.commit(item);
    }
}
