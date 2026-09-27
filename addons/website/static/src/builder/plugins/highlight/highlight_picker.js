import { onMounted, Component, onWillDestroy, signal, useProps, t } from "@odoo/owl";
import {
    applyTextHighlight,
    textHighlightFactory,
    getCurrentTextHighlight,
} from "@website/js/highlight_utils";

export class HighlightPicker extends Component {
    static template = "website.highlightPicker";
    props = useProps({
        selectHighlight: t.function(),
        previewHighlight: t.function(),
        revertHighlight: t.function(),
        style: t.string().optional(),
    });

    rootRef = signal.ref();
    setup() {
        onMounted(() => {
            for (const textEl of this.rootRef().querySelectorAll(".o_text_highlight")) {
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
