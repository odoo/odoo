import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import {
    useDropdownAutoVisibility,
    useToolbarDropdownFocus,
} from "@html_editor/toolbar_dropdown_hook";
import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useRef, useState } from "@web/owl2/utils";
import { useChildRef } from "@web/core/utils/hooks";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";

export class ImageAlignSelector extends Component {
    static template = "html_editor.ImageAlignSelector";
    static components = { Dropdown, DropdownItem };
    static props = {
        items: Array,
        getDisplay: Function,
        focusEditable: Function,
        onSelected: Function,
        ...toolbarButtonProps,
    };

    setup() {
        this.state = useState(this.props.getDisplay());
        this.menuRef = useChildRef();
        this.imageAlignSelector = useRef("imageAlignSelector");
        this.dropdown = useDropdownState();
        useToolbarDropdownFocus(this.dropdown, this.imageAlignSelector);
        useDropdownAutoVisibility(this.env.overlayState, this.menuRef);
    }

    onSelected(item) {
        this.props.onSelected(item);
        this.props.focusEditable();
    }
}
