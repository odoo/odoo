import { onMounted, useRef, Component, onWillDestroy } from "@odoo/owl";
import { applyTextHighlight, textHighlightFactory } from "@website/js/highlight_utils";

export class HighlightPicker extends Component {
    static template = "website.highlightPicker";
    static props = {
        selectHighlight: Function,
        previewHighlight: Function,
        resetHighlightPreview: Function,
    };

    setup() {
        const root = useRef("root");
        onMounted(() => {
            for (const textEl of root.el.querySelectorAll("[data-highlight-text]")) {
                applyTextHighlight(textEl, textEl.dataset.highlightText);
            }
        });

        onWillDestroy(() => {
            this.props.revertHighlight();
        });
    }
    getHighlightFactory() {
        return textHighlightFactory;
    }
}
