// @ts-check
/** @odoo-module native */

import { Component, useState } from "@odoo/owl";
import { highlightText } from "@web/core/utils/dom/html";
export class HighlightText extends Component {
    static template = "web.HighlightText";
    static props = {
        originalText: String,
    };
    /** @type {any} */
    searchState;

    setup() {
        /** @type {{ value: string }} */
        this.searchState = useState(this.env.searchState);
    }

    /** @returns {string | import("@odoo/owl").Markup} */
    get text() {
        return highlightText(
            this.searchState.value,
            this.props.originalText,
            "highlighter",
        );
    }
}
