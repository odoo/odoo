import { useState } from "@web/owl2/utils";
import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { useDropdownAutoVisibility } from "@html_editor/dropdown_autovisibility_hook";
import { useChildRef } from "@web/core/utils/hooks";

export class AlignSelector extends Component {
    static template = "html_editor.AlignSelector";
    static props = {
        getItems: Function,
        getDisplay: Function,
        onSelected: Function,
        ...toolbarButtonProps,
        applyAlignResetPreview: Function,
        applyAlignPreview: Function,
        applyAlignCommit: Function,
        overlay: { type: Object, optional: true },
    };
    static components = { Dropdown, DropdownItem };

    setup() {
        this.items = this.props.getItems();
        this.state = useState(this.props.getDisplay());
        this.menuRef = useChildRef();
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    onSelected(item) {
        this.props.overlay.bus.trigger("previewChange", {
            isPreviewActive: false,
        });
        this.props.applyAlignCommit(item, this.props.onSelected);
    }

    onItemHover(item) {
        this.props.overlay.bus.trigger("previewChange", {
            isPreviewActive: true,
        });
        this.props.applyAlignPreview(item, this.props.onSelected);
    }

    onItemHoverOut(item) {
        this.props.overlay.bus.trigger("previewChange", {
            isPreviewActive: false,
        });
        this.props.applyAlignResetPreview(item);
    }
}
