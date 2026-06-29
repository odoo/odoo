import { Component, computed, proxy } from "@odoo/owl";
import { highlightText } from "@web/core/utils/html";

export class HighlightText extends Component {
    static template = "web.HighlightText";
    static props = {
        originalText: String,
    };
    setup() {
        this.searchState = proxy(this.env.searchState);
        this.text = computed(() =>
            highlightText(this.searchState.value, this.props.originalText, "highlighter")
        );
    }
}
