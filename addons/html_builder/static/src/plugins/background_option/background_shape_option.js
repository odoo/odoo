import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { toRatio } from "@html_builder/utils/utils";
import { getBgImageURLFromEl } from "@html_builder/utils/utils_css";
import { _t } from "@web/core/l10n/translation";
import { ShapeSelector } from "@html_builder/plugins/shape/shape_selector";

export class BackgroundShapeOption extends BaseOptionComponent {
    static template = "html_builder.BackgroundShapeOption";
    static dependencies = ["backgroundShapeOption"];
    static components = { ShapeSelector };
    setup() {
        super.setup();
        this.backgroundShapePlugin = this.dependencies.backgroundShapeOption;
        this.toRatio = toRatio;
        this.shapePositionCache = this.extractShapePositionsFromCSS();
        this.state = useDomState((editingElement) => {
            const shapeData = this.backgroundShapePlugin.getShapeData(editingElement);
            this.currentColors = shapeData.colors;
            this.currentFlip = shapeData.flip;
            this.injectShapeColorStyles(editingElement);
            const shapeInfo = this.backgroundShapePlugin.getBackgroundShapes()[shapeData.shape];
            return {
                hasShape: !!shapeInfo,
                shapeName: shapeInfo?.selectLabel || _t("None"),
                isAnimated: shapeInfo?.animated,
                shapeColorNames: Object.keys(getDefaultColors(editingElement)),
            };
        });
    }
    getBackgroundShapeGroups() {
        return this.backgroundShapePlugin.getBackgroundShapeGroups();
    }
    getShapeStyleUrl(shapeId) {
        return this.backgroundShapePlugin.getShapeStyleUrl(shapeId);
    }
    getShapeClass(shapePath) {
        return `o_${shapePath.replaceAll("/", "_")}`;
    }

    /**
     * Extracts background-position values for all shapes directly from CSS
     * rules. This avoids the need to create temporary DOM elements.
     *
     * @returns {Map<string, string>} Map of shape class names to
     * background-position values
     */
    extractShapePositionsFromCSS() {
        const positions = new Map();
        const injectedStyleId = "shape-selector-custom-colors";

        for (const styleSheet of document.styleSheets) {
            // Skip cross-origin stylesheets
            if (styleSheet.href && new URL(styleSheet.href).origin !== location.origin) {
                continue;
            }
            // Skip the injected shape color stylesheet
            if (styleSheet.ownerNode?.id === injectedStyleId) {
                continue;
            }
            for (const rule of styleSheet.cssRules) {
                // Look for rules like
                // ".o_we_shape.o_html_builder_Connections_01"
                if (rule.selectorText?.includes(".o_we_shape.o_")) {
                    const match = rule.selectorText.match(/\.o_we_shape\.(o_[a-zA-Z0-9_]+)/);
                    if (match && rule.style.backgroundPosition) {
                        positions.set(match[1], rule.style.backgroundPosition);
                    }
                }
            }
        }

        return positions;
    }

    /**
     * Injects CSS to override shape background-image URLs with current colors
     * and applies flip transformations.
     * This allows the shape selector to show shapes with the user's selected
     * colors and flip.
     */
    injectShapeColorStyles(editingElement) {
        const styleId = "shape-selector-custom-colors";
        let styleEl = document.getElementById(styleId);

        if (!styleEl) {
            styleEl = document.createElement("style");
            styleEl.id = styleId;
            document.head.appendChild(styleEl);
        }

        // Build CSS rules for each shape
        const cssRules = [];
        const computedColors = { classic: {}, connection: {} };
        for (const group of Object.values(this.getBackgroundShapeGroups())) {
            for (const subgroup of Object.values(group.subgroups)) {
                for (const [shapePath] of Object.entries(subgroup.shapes)) {
                    const result = this.getShapeUrlWithColors(
                        editingElement,
                        shapePath,
                        computedColors
                    );
                    if (!result.hasChanges) {
                        continue;
                    }
                    const shapeClass = this.getShapeClass(shapePath);
                    const flipPosition = this.getFlipBackgroundPosition(shapePath);

                    const rule = `
                        .o_we_shape_btn_content .o_we_shape.${shapeClass} {
                            background-image: url("${result.url}") !important;
                            ${
                                flipPosition
                                    ? `background-position: ${flipPosition} !important;`
                                    : ""
                            }
                            }
                            `;
                    cssRules.push(rule);
                }
            }
        }

        styleEl.textContent = cssRules.join("\n");
    }

    /**
     * Generates a shape URL with current colors and flip applied.
     * Uses getImplicitColors to compute the correct colors for each shape.
     *
     * @param {string} editingElement - The editing Element
     * @param {string} shapePath - The shape path
     * @param {Object} computedColors - Cache object with classic and connection
     * colors
     * @returns {Object} Object with `url`, `hasChanges` flag, and
     * brighterColor`
     */
    getShapeUrlWithColors(editingElement, shapePath, computedColors) {
        const defaultUrl = this.getShapeStyleUrl(shapePath);

        if (!defaultUrl) {
            return { url: "", hasChanges: false };
        }
        const innerUrl = defaultUrl.replace(/^url\((['"]?)(.*?)\1\)$/, "$2");
        const url = new URL(innerUrl, window.location.origin);
        const defaultParams = new URLSearchParams(url.search);
        let hasChanges = false;
        const colorCache = shapePath.includes("html_builder/Connections/")
            ? computedColors.connection
            : computedColors.classic;

        let allColorsCached = true;
        for (const colorName of defaultParams.keys()) {
            if (!colorCache[colorName]) {
                allColorsCached = false;
                break;
            }
        }

        if (allColorsCached) {
            for (const [colorName, colorValue] of Object.entries(colorCache)) {
                if (defaultParams.has(colorName)) {
                    const currentValue = defaultParams.get(colorName);
                    if (currentValue !== colorValue) {
                        defaultParams.set(colorName, colorValue);
                        hasChanges = true;
                    }
                }
            }
        } else {
            if (this.backgroundShapePlugin.getImplicitColors && editingElement) {
                const implicitColors = this.backgroundShapePlugin.getImplicitColors(
                    editingElement,
                    shapePath,
                    this.currentColors || {}
                );
                for (const [colorName, colorValue] of Object.entries(implicitColors)) {
                    if (defaultParams.has(colorName)) {
                        colorCache[colorName] = colorValue;
                        const currentValue = defaultParams.get(colorName);
                        if (currentValue !== colorValue) {
                            defaultParams.set(colorName, colorValue);
                            hasChanges = true;
                        }
                    }
                }
            }
        }

        if (this.currentFlip && this.currentFlip.length > 0) {
            defaultParams.set("flip", this.currentFlip.sort().join(""));
            hasChanges = true;
        }

        return {
            url: `/html_editor/shape/${encodeURIComponent(
                shapePath
            )}.svg?${defaultParams.toString()}`,
            hasChanges,
        };
    }
    /**
     * Converts a CSS background-position value to a percentage.
     * Handles both numeric values and keywords like "left", "center", "right",
     * "top", "bottom".
     *
     * @param {string} position - The position value (e.g., "50%", "center",
     * "left", "100px")
     * @param {boolean} isVertical - Whether this is a vertical position
     * (affects keyword mapping)
     * @returns {number} The position as a percentage (0-100)
     */
    _convertPositionToPercent(position, isVertical = false) {
        position = position.trim();
        const keywordMap = isVertical
            ? { top: 0, center: 50, bottom: 100 }
            : { left: 0, center: 50, right: 100 };
        return keywordMap[position];
    }

    /**
     * Calculates the background-position value to apply flip transformations
     * for a given shape. Uses pre-extracted CSS positions to avoid DOM
     * manipulation.
     *
     * @param {string} shapePath - The path of the shape
     * (e.g., "html_builder/Connections/01")
     * @returns {string} The flipped background-position
     */
    getFlipBackgroundPosition(shapePath) {
        if (!this.currentFlip || this.currentFlip.length === 0) {
            return null;
        }
        const shapeClass = this.getShapeClass(shapePath);
        const bgPosition = this.shapePositionCache.get(shapeClass);
        const positions = bgPosition.split(" ");
        const firstTerm = positions[0];
        const secondTerm = positions[1];

        let xPos, yPos;
        // Check if first term is a vertical-only keyword
        if (firstTerm === "top" || firstTerm === "bottom") {
            xPos = this._convertPositionToPercent(secondTerm || "center", false);
            yPos = this._convertPositionToPercent(firstTerm, true);
        } else {
            xPos = this._convertPositionToPercent(firstTerm, false);
            yPos = this._convertPositionToPercent(secondTerm || "center", true);
        }

        xPos = this.currentFlip.includes("x") ? 100 - xPos : xPos;
        yPos = this.currentFlip.includes("y") ? 100 - yPos : yPos;
        return `${xPos}% ${yPos}%`;
    }
}

/**
 * Returns the default colors for the currently selected shape.
 *
 * @param {HTMLElement} editingElement the element on which to read the
 * shape data.
 */
export function getDefaultColors(editingElement) {
    const shapeContainerEl = editingElement.querySelector(":scope > .o_we_shape");
    if (!shapeContainerEl) {
        return {};
    }
    const shapeContainerClonedEl = shapeContainerEl.cloneNode(true);
    shapeContainerClonedEl.classList.add("d-none");
    // Needs to be in document for bg-image class to take effect
    editingElement.ownerDocument.body.appendChild(shapeContainerClonedEl);
    shapeContainerClonedEl.style.setProperty("background-image", "");
    const shapeSrc = shapeContainerClonedEl && getBgImageURLFromEl(shapeContainerClonedEl);
    shapeContainerClonedEl.remove();
    if (!shapeSrc) {
        return {};
    }
    const url = new URL(shapeSrc, window.location.origin);
    return Object.fromEntries(url.searchParams.entries());
}
