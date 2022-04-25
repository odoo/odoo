/** @odoo-module */

import { Dialog } from "../dialog/dialog";
import { ColorPicker } from "./colorpicker";
import { _lt } from "../l10n/translation";

const { Component } = owl;

export class ColorPickerDialog extends Component {
    setup() {
        this.currentlySelectedColor = this.props.color;
    }

    onColorSelected({ hex }) {
        this.currentlySelectedColor = hex;
    }

    choose() {
        this.props.onColorSelected(this.currentlySelectedColor);
        this.props.close();
    }
}
ColorPickerDialog.components = { Dialog, ColorPicker };
ColorPickerDialog.template = "web.ColorPickerDialog";
ColorPickerDialog.title = _lt("Pick a color");
ColorPickerDialog.props = {
    color: { type: String, optional: true },
    close: Function,
    onColorSelected: Function,
};
ColorPickerDialog.defaultProps = {
    color: "#ff0000",
};
