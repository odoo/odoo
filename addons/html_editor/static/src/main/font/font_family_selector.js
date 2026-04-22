import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { useDropdownAutoVisibility } from "@html_editor/dropdown_autovisibility_hook";
import { useChildRef } from "@web/core/utils/hooks";

export class FontFamilySelector extends Component {
    static template = "html_editor.FontFamilySelector";
    static props = {
        document: { optional: true },
        fontFamilyItems: Object,
        currentFontFamily: Object,
        onSelected: Function,
        ...toolbarButtonProps,
        applyFontFamilyResetPreview: Function,
        applyFontFamliyPreview: Function,
        applyFontFamilyCommit: Function,
        overlay: { type: Object, optional: true },
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.menuRef = useChildRef();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    onSelected(item) {
        this.props.overlay.bus.trigger("previewChange", {
            isPreviewActive: false,
        });
        this.props.applyFontFamilyCommit(item, this.props.onSelected);
    }

    onItemHover(item) {
        this.props.overlay.bus.trigger("previewChange", {
            isPreviewActive: true,
        });
        this.props.applyFontFamliyPreview(item, this.props.onSelected);
    }

    onItemHoverOut(item) {
        this.props.overlay.bus.trigger("previewChange", {
            isPreviewActive: false,
        });
        this.props.applyFontFamilyResetPreview(item);
    }
}
