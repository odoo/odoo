import { onMounted, Component, onWillDestroy, signal, useProps, t } from "@odoo/owl";
import {
    applyTextHighlight,
    textHighlightFactory,
    getCurrentTextHighlight,
} from "@website/js/highlight_utils";

export const highlightIdToName = {
    underline: "Underline",
    freehand_1: "Freehand 1",
    freehand_2: "Freehand 2",
    freehand_3: "Freehand 3",
    double: "Double",
    wavy: "Wavy",
    circle_1: "Circle 1",
    circle_2: "Circle 2",
    circle_3: "Circle 3",
    over_underline: "Over and underline",
    scribble_1: "Scribble 1",
    scribble_2: "Scribble 2",
    scribble_3: "Scribble 3",
    scribble_4: "Scribble 4",
    jagged: "Jagged",
    cross: "Cross",
    diagonal: "Diagonal",
    strikethrough: "Strikethrough",
    bold: "Bold",
    bold_1: "Bold 1",
    bold_2: "Bold 2",
};

/**
 * Menu of the highlight shapes: one row per shape, with a sample drawn in the
 * current color and thickness, and its name.
 */
export class HighlightPicker extends Component {
    static template = "website.highlightPicker";
    props = useProps({
        selectHighlight: t.function(),
        previewHighlight: t.function(),
        revertHighlight: t.function(),
        currentHighlightId: t.string().optional(),
        removeHighlight: t.function().optional(),
        style: t.string().optional(),
    });

    rootRef = signal.ref();
    setup() {
        this.highlightIdToName = highlightIdToName;
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
