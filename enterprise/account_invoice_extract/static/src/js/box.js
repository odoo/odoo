/** @odoo-module **/

import { Component } from "@odoo/owl";

export class Box extends Component {
    static template = "account_invoice_extract.Box";
    static props = {
        box: Object,
        pageWidth: String,
        pageHeight: String,
        onClickBoxCallback: Function,
    };
    /**
     * @override
     */
    setup() {
        this.state = this.props.box;
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get style() {
        const style = [
            `left: calc(${this.state.box_midX} * ${this.props.pageWidth})`,
            `top: calc(${this.state.box_midY} * ${this.props.pageHeight})`,
            `width: calc(${this.state.box_width} * ${this.props.pageWidth})`,
            `height: calc(${this.state.box_height} * ${this.props.pageHeight})`,
            `transform: translate(-50%, -50%) rotate(${this.state.box_angle}deg)`,
            `-ms-transform: translate(-50%, -50%) rotate(${this.state.box_angle}deg)`,
            `-webkit-transform: translate(-50%, -50%) rotate(${this.state.box_angle}deg)`,
        ].join('; ');
        return style;
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    onClick() {
        this.props.onClickBoxCallback(this.state.id, this.state.page);
    }
};
