import { proxy } from "@odoo/owl";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { ColorSelector } from "./color_selector";
import { isStylable, isTextNode } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { isCSSColor, normalizeCSSColor, RGBA_REGEX } from "@web/core/utils/colors";
import { withSequence } from "@html_editor/utils/resource";

const RGBA_OPACITY = 0.6;
const HEX_OPACITY = "99";

/**
 * @typedef { Object } ColorUIShared
 * @typedef {(() => string)[]} selected_background_color_providers
 * @property { ColorUIPlugin['getPropsForColorSelector'] } getPropsForColorSelector
 */

export class ColorUIPlugin extends Plugin {
    static id = "colorUi";
    static dependencies = ["color", "history", "selection", "format"];
    static shared = ["getPropsForColorSelector"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        toolbar_items: [
            {
                id: "forecolor",
                groupId: "decoration",
                namespaces: ["compact", "expanded"],
                description: _t("Apply Font Color"),
                Component: ColorSelector,
                props: this.getPropsForColorSelector("foreground"),
                isAvailable: isHtmlContentSupported,
                isDisabled: (sel, nodes) => nodes.some((node) => !isStylable(node)),
            },
            {
                id: "backcolor",
                groupId: "decoration",
                description: _t("Apply Background Color"),
                Component: ColorSelector,
                props: this.getPropsForColorSelector("background"),
                isAvailable: isHtmlContentSupported,
                isDisabled: (sel, nodes) => nodes.some((node) => !isStylable(node)),
            },
        ],
        on_selectionchange_handlers: withSequence(100, this.updateSelectedColor.bind(this)),
        on_format_requested_handlers: this.updateSelectedColor.bind(this),
        background_color_processors: this.getBackgroundColorProcessor.bind(this),
        /** Providers */
        selected_background_color_providers: withSequence(
            10,
            this.computeBackgroundColorForTextNode.bind(this)
        ),
    };

    setup() {
        this.selectedColors = proxy({ color: "", backgroundColor: "" });
        this.previewableApplyColor = this.dependencies.history.makePreviewableOperation(
            (color, mode) => {
                if (mode === "backgroundColor" && color) {
                    color = this.applyBackgroundColorProcessor(color);
                }
                this.dependencies.format.requestFormat(mode, {
                    applyStyle: color !== "",
                    formatProps: color ? { color } : undefined,
                    commit: false,
                });
            }
        );
    }

    /**
     * @param {'foreground'|'background'} type
     */
    getPropsForColorSelector(type) {
        const mode = type === "foreground" ? "color" : "backgroundColor";
        return {
            type,
            mode,

            getUsedCustomColors: () => this.getUsedCustomColors(mode),
            getSelectedColors: () => this.selectedColors,
            applyColor: (color) => this.applyColorCommit({ color, mode }),
            applyColorPreview: (color) => this.applyColorPreview({ color, mode }),
            applyColorResetPreview: this.applyColorResetPreview.bind(this),
            colorPrefix: mode === "color" ? "text-" : "bg-",
            onClose: (res) => {
                // onClose receives "escape" when closed via Escape,
                // otherwise undefined. Focus editable only for non-escape closes.
                !res && this.dependencies.selection.focusEditable();
            },
            getTargetedElements: () => {
                const nodes = this.dependencies.selection.getTargetedNodes().filter(isTextNode);
                return nodes.map((node) => closestElement(node));
            },
        };
    }

    /**
     * Apply a css or class color on the current selection (wrapped in a span).
     *
     * @param {Object} param
     * @param {string} param.color hexadecimal or bg-name/text-name class
     * @param {string} param.mode 'color' or 'backgroundColor'
     */
    applyColorCommit({ color, mode }) {
        this.previewableApplyColor.commit(color, mode);
        this.updateSelectedColor();
    }
    /**
     * Apply a css or class color on the current selection (wrapped in a span)
     * in preview mode so that it can be reset.
     *
     * @param {Object} param
     * @param {string} param.color hexadecimal or bg-name/text-name class
     * @param {string} param.mode 'color' or 'backgroundColor'
     */
    applyColorPreview({ color, mode }) {
        // Preview the color before applying it.
        this.previewableApplyColor.preview(color, mode);
        this.updateSelectedColor();
    }
    /**
     * Reset the color applied in preview mode.
     */
    applyColorResetPreview() {
        this.previewableApplyColor.revert();
        this.updateSelectedColor();
    }

    getUsedCustomColors(mode) {
        const allSpans = this.editable.querySelectorAll("span");
        const usedCustomColors = new Set();
        for (const span of allSpans) {
            if (isCSSColor(span.style[mode])) {
                usedCustomColors.add(normalizeCSSColor(span.style[mode]));
            }
        }
        return usedCustomColors;
    }

    computeBackgroundColorForTextNode() {
        const nodes = this.dependencies.selection.getTargetedNodes().filter(isTextNode);
        if (nodes.length === 0) {
            return;
        }
        const el = closestElement(nodes[0]);
        if (!el) {
            return;
        }

        return this.dependencies.color.getElementColors(el).backgroundColor;
    }

    updateSelectedColor() {
        // Compute and update the background color.
        let backgroundColor;
        for (const provider of this.getResource("selected_background_color_providers")) {
            const providedBackgroundColor = provider();
            if (providedBackgroundColor) {
                backgroundColor = providedBackgroundColor;
                break;
            }
        }

        const { color: colorIntent, backgroundColor: bgIntent } =
            this.dependencies.format.getPendingIntents();
        const pendingColor = colorIntent && (colorIntent.formatProps?.color ?? "");
        const pendingBgColor = bgIntent && (bgIntent.formatProps?.color ?? "");

        this.selectedColors.backgroundColor = pendingBgColor ?? (backgroundColor || "#00000000");

        // Compute and update the text color.
        const nodes = this.dependencies.selection.getTargetedNodes().filter(isTextNode);
        if (nodes.length === 0) {
            this.selectedColors.color = pendingColor ?? "";
            return;
        }
        const el = closestElement(nodes[0]);
        if (!el) {
            this.selectedColors.color = pendingColor ?? "";
            return;
        }
        const fromDom = this.dependencies.color.getElementColors(el);
        this.selectedColors.color = pendingColor ?? fromDom.color;
    }

    getBackgroundColorProcessor(backgroundColor) {
        const activeTab = document
            .querySelector(".o_font_color_selector button.active")
            ?.innerHTML.trim();
        if (backgroundColor.startsWith("rgba") && (!activeTab || activeTab === "Solid")) {
            // Buttons in the solid tab of color selector have no
            // opacity, hence to match selected color correctly,
            // we need to remove applied 0.6 opacity.
            const values = backgroundColor.match(RGBA_REGEX) || [];
            const alpha = parseFloat(values.pop()); // Extract alpha value
            if (alpha === RGBA_OPACITY) {
                backgroundColor = `rgb(${values.slice(0, 3).join(", ")})`; // Remove alpha
            }
        }
        return backgroundColor;
    }

    applyBackgroundColorProcessor(brackgroundColor) {
        const activeTab = document
            .querySelector(".o_font_color_selector button.active")
            ?.innerHTML.trim();
        if (activeTab === "Solid" && brackgroundColor.startsWith("#")) {
            // Apply default transparency to selected solid tab colors in background
            // mode to make text highlighting more usable between light and dark modes.
            brackgroundColor += HEX_OPACITY;
        }
        return brackgroundColor;
    }
}
