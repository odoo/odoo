import { escapeRegExp } from "@web/core/utils/strings";

import { Component, useState, onWillRender } from "@odoo/owl";

export class HighlightText extends Component {
    static template = "web.HighlightText";
    static highlightClass = "highlighter";
    static props = {
        originalText: String,
    };
    setup() {
        this.searchState = useState(this.env.searchState);

        onWillRender(() => {
            const splitText = this.props.originalText.split(
                new RegExp(`(${escapeRegExp(this.searchState.value)})`, "ig")
            );
            this.splitText =
                this.searchState.value.length && splitText.length > 1
                    ? splitText
                    : [this.props.originalText];
        });
    }
}
