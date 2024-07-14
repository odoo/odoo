/** @odoo-module **/

import { Box } from '@account_invoice_extract/js/box';
import { Component } from "@odoo/owl";

export class BoxLayer extends Component {
    /**
     * @override
     */
    setup() {
        this.state = {
            boxes: this.props.boxes,
        };

        // Used to define the style of the contained boxes
        if (this.isOnPDF) {
            this.pageWidth = this.props.pageLayer.style.width;
            this.pageHeight = this.props.pageLayer.style.height;
        } else if (this.isOnImg) {
            this.pageWidth = this.props.pageLayer.clientWidth;
            this.pageHeight = this.props.pageLayer.clientHeight;
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    get style() {
        if (this.isOnPDF) {
            return 'width: ' + this.props.pageLayer.style.width + '; ' +
                   'height: ' + this.props.pageLayer.style.height + ';';
        } else if (this.isOnImg) {
            return 'width: ' + this.props.pageLayer.clientWidth + 'px; ' +
                   'height: ' + this.props.pageLayer.clientHeight + 'px; ' +
                   'left: ' + this.props.pageLayer.offsetLeft + 'px; ' +
                   'top: ' + this.props.pageLayer.offsetTop + 'px;';
        }
    }

    get isOnImg() {
        return this.props.mode === 'img';
    }

    get isOnPDF() {
        return this.props.mode === 'pdf';
    }
};

BoxLayer.components = { Box };
BoxLayer.template = 'account_invoice_extract.BoxLayer';
