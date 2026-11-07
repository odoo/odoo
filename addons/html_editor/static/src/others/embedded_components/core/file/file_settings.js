import { Component, onMounted, signal, t, useListener, useProps } from "@odoo/owl";
import { CheckboxItem } from "@web/core/dropdown/checkbox_item";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class FileSettings extends Component {
    static template = "html_editor.FileSettings";
    static components = { CheckboxItem, Dropdown, DropdownItem };
    props = useProps({
        dropdown: t.object().optional(),
        closeOverlay: t.function().optional(),
        fileModel: t.object(),
        isPreviewInline: t.boolean().optional(false),
        download: t.function(),
        rename: t.function().optional(),
        toggleInlinePreview: t.function().optional(),
        remove: t.function().optional(),
        isOverlay: t.boolean().optional(),
        host: t.object(),
    });

    menuRef = signal.ref();

    setup() {
        onMounted(() => {
            this.menuRef()?.addEventListener("pointerleave", () => {
                if (!this.props.dropdown?.isOpen) {
                    this.props.closeOverlay?.();
                }
            });
        });

        useListener(document, "pointerdown", () => {
            if (this.props.dropdown?.isOpen) {
                return;
            }
            this.props.closeOverlay?.();
        });
    }
}
