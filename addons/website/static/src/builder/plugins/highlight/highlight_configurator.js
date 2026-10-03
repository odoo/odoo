import { Component, proxy, signal, useEffect, useProps, t } from "@odoo/owl";
import { ColorPicker } from "@html_editor/components/color_picker/color_picker";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { HighlightPicker, highlightIdToName } from "./highlight_picker";
import { applyTextHighlight } from "@website/js/highlight_utils";
import { normalizeColor } from "@html_builder/utils/utils_css";
import { getHtmlStyle } from "@html_editor/utils/formatting";

export { highlightIdToName };

export class HighlightConfigurator extends Component {
    static template = "website.highlightConfigurator";
    static components = { ColorPicker, Dropdown, HighlightPicker };
    props = useProps({
        applyHighlight: t.function(),
        applyHighlightStyle: t.function(),
        deleteHighlight: t.function(),
        getHighlightState: t.function(),
        previewHighlight: t.function(),
        previewHighlightStyle: t.function(),
        revertHighlight: t.function(),
        revertHighlightStyle: t.function(),
        componentStack: t.object(),
        getUsedCustomColors: t.function(),
    });

    sampleRef = signal.ref();

    setup() {
        this.state = proxy(this.props.getHighlightState());
        this.highlightIdToName = highlightIdToName;
        this.dropdown = useDropdownState();
        // Draw the current shape, color and thickness on the sample of the
        // Shape select.
        useEffect(() => {
            const sampleEl = this.sampleRef();
            const { highlightId } = this.state;
            if (!sampleEl || !highlightId) {
                return;
            }
            for (const svg of sampleEl.querySelectorAll("svg")) {
                svg.remove();
            }
            applyTextHighlight(sampleEl, highlightId);
        });
    }

    /**
     * Color and thickness of the samples, the thickness kept readable at the
     * size of the panel text.
     */
    get sampleStyle() {
        const { color, thickness } = this.state;
        return [
            `--text-highlight-color: ${color || "var(--hb-cp-o-color-1)"}`,
            `--text-highlight-width: ${Math.min(Math.max(thickness || 2, 1), 3)}px`,
        ].join("; ");
    }

    openColorPicker() {
        this.props.componentStack.push(
            ColorPicker,
            {
                state: { selectedColor: this.state.color, defaultTab: "solid" },
                colorPrefix: "hb-cp-",
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
                cssVarColorPrefix: "hb-cp-",
            },
            "Select a color",
            true
        );
    }

    selectHighlight(highlightId) {
        this.dropdown.close();
        this.props.applyHighlight(highlightId);
    }

    selectHighlightColor(color) {
        this.props.componentStack.pop();
        const highlightColor = color.startsWith("hb-cp-")
            ? `var(--${color.replace("hb-cp-", "")})`
            : normalizeColor(color, getHtmlStyle(document));
        this.props.applyHighlightStyle("--text-highlight-color", highlightColor);
    }

    removeHighlight() {
        this.dropdown.close();
        this.props.deleteHighlight();
    }

    onThicknessChange(ev) {
        this.props.applyHighlightStyle(
            "--text-highlight-width",
            ev.target.value ? ev.target.value + "px" : ""
        );
    }
}
