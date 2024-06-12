/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

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
    _t("No color"),
    _t("Red"),
    _t("Orange"),
    _t("Yellow"),
    _t("Cyan"),
    _t("Purple"),
    _t("Almond"),
    _t("Teal"),
    _t("Blue"),
    _t("Raspberry"),
    _t("Green"),
    _t("Violet"),
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
