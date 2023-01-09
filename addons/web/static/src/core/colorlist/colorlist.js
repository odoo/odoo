/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";

import { Component, useRef, useState, useExternalListener } from "@odoo/owl";

export class ColorList extends Component {
    setup() {
        this.colorlistRef = useRef("colorlist");
        this.state = useState({ isExpanded: this.props.isExpanded });
        useExternalListener(window, "click", this.onOutsideClick);
    }
    get colors() {
        return this.constructor.COLORS;
    }
    onColorSelected(id) {
        this.props.onColorSelected(id);
        if (!this.props.forceExpanded) {
            this.state.isExpanded = false;
        }
    }
    onOutsideClick(ev) {
        if (this.colorlistRef.el.contains(ev.target) || this.props.forceExpanded) {
            return;
        }
        this.state.isExpanded = false;
    }
    onToggle(ev) {
        if (this.props.canToggle) {
            ev.preventDefault();
            ev.stopPropagation();
            this.state.isExpanded = !this.state.isExpanded;
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
ColorList.defaultProps = {
    forceExpanded: false,
    isExpanded: false,
};
ColorList.props = {
    canToggle: { type: Boolean, optional: true },
    colors: Array,
    forceExpanded: { type: Boolean, optional: true },
    isExpanded: { type: Boolean, optional: true },
    onColorSelected: Function,
    selectedColor: { type: Number, optional: true },
};
