import { Component, onWillStart, useState } from "@odoo/owl";
import { ColorPicker } from "@web/core/color_picker/color_picker";
import { HighlightPicker } from "./highlight_picker";
import { normalizeColor } from "@html_builder/utils/utils_css";
import { getHtmlStyle } from "@html_editor/utils/formatting";

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

export class HighlightConfigurator extends Component {
    static template = "website.highlightConfigurator";
    static components = { ColorPicker };
    static props = {
        applyHighlight: Function,
        applyHighlightStyle: Function,
        deleteHighlight: Function,
        getHighlightState: Function,
        previewHighlight: Function,
        previewHighlightStyle: Function,
        revertHighlight: Function,
        revertHighlightStyle: Function,
        componentStack: Object,
        getUsedCustomColors: Function,
    };

    setup() {
        this.state = useState(this.props.getHighlightState());
        this.highlightIdToName = highlightIdToName;
        onWillStart(() => {
            if (!this.state.highlightId) {
                this.openHighlightPicker(false);
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
                state: { selectedColor: this.state.color, defaultTab: "solid" },
                colorPrefix: "",
                getUsedCustomColors: this.props.getUsedCustomColors,
                enabledTabs: ["solid", "custom"],
                applyColor: this.selectHighlightColor.bind(this),
                applyColorPreview: (color) =>
                    this.props.previewHighlightStyle(
                        "--text-highlight-color",
                        normalizeColor(color, getHtmlStyle(document))
                    ),
                applyColorResetPreview: this.props.revertHighlightStyle,
                className: "d-contents",
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
        this.props.applyHighlightStyle(
            "--text-highlight-color",
            normalizeColor(color, getHtmlStyle(document))
        );
    }

    deleteHighlight() {
        this.props.deleteHighlight();
        this.openHighlightPicker(false);
    }

    onThicknessChange(ev) {
        this.props.applyHighlightStyle(
            "--text-highlight-width",
            ev.target.value ? ev.target.value + "px" : ""
        );
    }
}
