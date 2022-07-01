/** @odoo-module **/
import { escapeRegExp } from "@web/core/utils/strings";

const { Component, useState, onWillRender } = owl;

export class HighlightText extends Component {
    setup() {
        this.searchValue = useState(this.env.searchValue);

        onWillRender(() => {
            const splitText = this.props.originalText.split(
                new RegExp(`(${escapeRegExp(this.searchValue.value)})`, "ig")
            );
            this.splitText =
                this.searchValue.value.length && splitText.length > 1
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
