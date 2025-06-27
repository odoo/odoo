import { Component, useState, onWillRender } from "@odoo/owl";
import { highlightText } from "@web/core/utils/html";

export class HighlightText extends Component {
    static template = "web.HighlightText";
    static props = {
        originalText: String,
    };
    setup() {
        this.searchState = useState(this.env.searchState);

        onWillRender(() => {
            this.text = highlightText(
                this.searchState.value,
                this.props.originalText,
                "highlighter"
            );
        });
    }
}
