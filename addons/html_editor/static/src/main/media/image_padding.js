import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class ImagePadding extends Component {
    static components = { Dropdown, DropdownItem };
    static props = {
        dispatch: Function,
    };
    static template = "html_editor.ImagePadding";

    setup() {
        this.paddings = { None: 0, Small: 1, Medium: 2, Large: 3, XL: 5 };
    }

    onSelected(padding) {
        this.props.dispatch("SET_IMAGE_PADDING", { padding: this.paddings[padding] });
    }
}
