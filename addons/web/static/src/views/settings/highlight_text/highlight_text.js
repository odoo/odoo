// @ts-check

/** @module @web/views/settings/highlight_text/highlight_text - Component rendering text with the current search term highlighted via markup */

import { Component, onWillRender, useState } from "@odoo/owl";
import { highlightText } from "@web/core/utils/dom/html";
/** Renders text with the current search term highlighted via markup. */
export class HighlightText extends Component {
    static template = "web.HighlightText";
    static props = {
        originalText: String,
    };
    /**
     * Subscribe to env search state and recompute highlighted markup before each render.
     */
    setup() {
        /** @type {{ value: string }} */
        this.searchState = useState(this.env.searchState);

        onWillRender(() => {
            /** @type {import("@odoo/owl").Markup} */
            this.text = highlightText(
                this.searchState.value,
                this.props.originalText,
                "highlighter",
            );
        });
    }
}
