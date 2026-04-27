/** @odoo-module **/

import { Box } from '@account_invoice_extract/js/box';
import { Component } from "@odoo/owl";

export class BoxLayer extends Component {
    static components = { Box };
    static template = "account_invoice_extract.BoxLayer";
    static props = {
        boxes: Array,
        pageLayer: {
            validate: (pageLayer) => {
                // target may be inside an iframe, so get the Element constructor
                // to test against from its owner document's default view
                const Element = pageLayer?.ownerDocument?.defaultView?.Element;
                return (
                    (Boolean(Element) &&
                        (pageLayer instanceof Element || pageLayer instanceof window.Element)) ||
                    (typeof pageLayer === "object" && pageLayer?.constructor?.name?.endsWith("Element"))
                );
            },
        },
        onClickBoxCallback: Function,
        mode: String,
    };
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
            this.pageWidth = `${this.props.pageLayer.clientWidth}px`;
            this.pageHeight = `${this.props.pageLayer.clientHeight}px`;
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
