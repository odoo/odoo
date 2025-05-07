import { Component, onMounted, useEffect, useRef, useState } from "@odoo/owl";
import { ColorPicker } from "@web/core/color_picker/color_picker";
import { HighlightPicker } from "./highlight_picker";
import { applyTextHighlight } from "@website/js/highlight_utils";

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
    bold1: "Bold 1",
    bold2: "Bold 2",
};

export class HighlightConfigurator extends Component {
    static template = "website.highlightConfigurator";
    static components = { ColorPicker };
    static props = {
        applyHighlight: Function,
        applyHighlightStyle: Function,
        getHighlightState: Function,
        getSelection: Function,
        previewHighlight: Function,
        previewHighlightStyle: Function,
        revertHighlight: Function,
        revertHighlightStyle: Function,
        componentStack: Object,
    };

    setup() {
        this.state = useState(this.props.getHighlightState());
        this.highlightIdToName = highlightIdToName;
        this.preview = useRef("preview");
        onMounted(() => {
            if (!this.state.highlightId) {
                this.openHighlightPicker(false);
            }
            if (this.state.highlightId && this.preview.el) {
                applyTextHighlight(this.preview.el, this.state.highlightId);
            }
        });
    }

    openHighlightPicker(withPrevious = true) {
        this.props.componentStack.push(
            HighlightPicker,
            {
                selectHighlight: this.selectHighlight.bind(this),
                previewHighlight: this.props.previewHighlight,
                revertHighlight: this.props.revertHighlight,
            },
            "Select a highlight",
            withPrevious
        );
    }

    openColorPicker() {
        this.props.componentStack.push(
            ColorPicker,
            {
                state: { selectedColor: this.state.color },
                //TODO: implement customColors
                getUsedCustomColors: () => {},
                applyColor: this.selectHighlightColor.bind(this),
                applyColorPreview: (color) =>
                    this.props.previewHighlightStyle("--text-highlight-color", color),
                applyColorResetPreview: this.props.revertHighlightStyle,
            },
            "Select a color",
            true
        );
    }

    selectHighlight(highlightId) {
        this.props.componentStack.pop();
        this.props.applyHighlight(highlightId);
    }

    selectHighlightColor(color) {
        this.props.componentStack.pop();
        this.props.applyHighlightStyle("--text-highlight-color", color);
    }

    onThicknessChange(ev) {
        this.props.applyHighlightStyle(
            "--text-highlight-width",
            ev.target.value ? ev.target.value + "px" : ""
        );
    }
}
