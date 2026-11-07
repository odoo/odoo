/** @odoo-module **/
import { escapeRegExp } from "@web/core/utils/strings";

import { Component, useState, onWillRender } from "@odoo/owl";

export class HighlightText extends Component {
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
HighlightText.template = "web.HighlightText";
HighlightText.props = {
    originalText: String,
};
HighlightText.highlightClass = "highlighter";
