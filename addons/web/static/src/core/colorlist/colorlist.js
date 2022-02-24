/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";

const { Component, useState } = owl;

export class ColorList extends Component {
    setup() {
        this.state = useState({
            currentColorIndex: 0,
        });
    }

    get currentColor() {
        return ColorList.RECORD_COLORS[this.state.currentColorIndex];
    }

    onColorSelected(id) {
        this.state.currentColorIndex = id;
        this.props.onColorSelected(id);
    }
}

ColorList.template = "web.ColorList";
ColorList.props = {
    colors: Array,
    onColorSelected: Function,
};
