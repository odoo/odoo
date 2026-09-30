import { onMounted, useRef, Component, onWillDestroy } from "@odoo/owl";
import {
    applyTextHighlight,
    textHighlightFactory,
    getCurrentTextHighlight,
} from "@website/js/highlight_utils";

export class HighlightPicker extends Component {
    static template = "website.highlightPicker";
    static props = {
        selectHighlight: Function,
        previewHighlight: Function,
        revertHighlight: Function,
        style: { type: String, optional: true },
    };

    setup() {
        const root = useRef("root");
        onMounted(() => {
            for (const textEl of root.el.querySelectorAll(".o_text_highlight")) {
                const highlightId = getCurrentTextHighlight(textEl);
                applyTextHighlight(textEl, highlightId);
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
