/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";

const { Component, useRef, useState, useExternalListener } = owl;

export class ColorList extends Component {
    setup() {
        this.colorlistRef = useRef("colorlist");
        this.state = useState({ isExpanded: false });
        useExternalListener(window, "click", this.onOutsideClick);
    }
    get colors() {
        return this.constructor.COLORS;
    }
    onColorSelected(id) {
        this.props.onColorSelected(id);
        this.state.isExpanded = false;
    }
    onOutsideClick(ev) {
        if (this.colorlistRef.el.contains(ev.target)) return;
        this.state.isExpanded = false;
    }
    onToggle(focus = true) {
        this.state.isExpanded = !this.state.isExpanded;
        if (focus) {
            this.colorlistRef.el.firstElementChild.focus();
        }
    }
}

ColorList.COLORS = [
    _lt("No color"),
    _lt("Red"),
    _lt("Orange"),
    _lt("Yellow"),
    _lt("Light blue"),
    _lt("Dark purple"),
    _lt("Salmon pink"),
    _lt("Medium blue"),
    _lt("Dark blue"),
    _lt("Fuchsia"),
    _lt("Green"),
    _lt("Purple"),
];
ColorList.template = "web.ColorList";
ColorList.props = {
    colors: Array,
    isExpanded: { type: Boolean, optional: true },
    onColorSelected: Function,
    togglerColor: { type: Number, optional: true },
};
