import { getValueFromVar } from "@html_builder/utils/utils";
import { normalizeColor } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { backgroundShapesDefinition } from "./background_shapes_definition";
import { getDefaultColors } from "./background_shape_option";
import { withSequence } from "@html_editor/utils/resource";
import { getBgImageURLFromURL } from "@html_editor/utils/image";
import { BuilderAction } from "@html_builder/core/builder_action";
import { getHtmlStyle, getCSSVariableValue } from "@html_editor/utils/formatting";
import { rgbToHex } from "@web/core/utils/colors";

/**
 * @typedef {((editingElement: HTMLElement) => HTMLElement)[]} background_shape_target_providers
 */

export class BackgroundShapeOptionPlugin extends Plugin {
    static id = "backgroundShapeOption";
    static dependencies = ["customizeTab"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_actions: {
            SetBackgroundShapeAction,
            ShowOnMobileAction,
            FlipShapeAction,
            SetBgAnimationSpeedAction,
            BackgroundShapeColorAction,
        },
        background_shape_target_providers: withSequence(5, (editingElement) =>
            editingElement.querySelector(":scope > .o_we_bg_filter")
        ),
        content_not_editable_selectors: ".o_we_shape",
        system_node_selectors: ".o_we_shape",
    };
    static shared = [
        "getShapeStyleUrl",
        "getShapeData",
        "getBackgroundShapeGroups",
        "getBackgroundShapes",
        "getImplicitColors",
        "applyShape",
        "createShapeContainer",
    ];
    setup() {
        // TODO: update shapeBackgroundImagePerClass if a stylesheet value
        // changes.
        this.shapeBackgroundImagePerClass = {};
        for (const styleSheet of this.document.styleSheets) {
            if (styleSheet.href && new URL(styleSheet.href).host !== location.host) {
                // In some browsers, if a stylesheet is loaded from a different
                // domain accessing cssRules results in a SecurityError.
                continue;
            }
            for (const rule of [...styleSheet.cssRules]) {
                if (rule.selectorText && rule.selectorText.startsWith(".o_we_shape.")) {
                    this.shapeBackgroundImagePerClass[rule.selectorText] =
                        rule.style.backgroundImage;
                }
            }
        }
        // Flip classes should no longer be used but are still present in some
        // theme snippets.
        const flipEls = [...this.editable.querySelectorAll(".o_we_flip_x, .o_we_flip_y")];
        for (const flipEl of flipEls) {
            this.applyShape(flipEl, () => ({ flip: this.getShapeData(flipEl).flip }));
        }
    }
    /**
     * Handles everything related to saving state before preview and restoring
     * it after a preview or locking in the changes when not in preview.
     *
     * @param {HTMLElement} editingElement - The element being edited
     * @param {Function} computeShapeData - Function to compute the new shape
     * data.
     */
    applyShape(editingElement, computeShapeData) {
        const newShapeData = computeShapeData();
        const changedShape = !!newShapeData.shape;
        this.markShape(editingElement, newShapeData);

        // Updates/removes the shape container as needed and gives it the
        // correct background shape
        const json = editingElement.dataset.oeShapeData;
        const {
            shape,
            colors,
            flip = [],
            animated = "false",
            showOnMobile,
            shapeAnimationSpeed,
        } = json ? JSON.parse(json) : {};

        let shapeContainerEl = editingElement.querySelector(":scope > .o_we_shape");

        if (!shape) {
            return this.insertShapeContainer(editingElement, null);
        }

        if (changedShape) {
            // Reset shape container when shape changes (e.g., for transparent
            // color)
            shapeContainerEl = this.createShapeContainer(editingElement, shape);
        }

        // Remove old flip classes (flipping is now done via SVG)
        shapeContainerEl.classList.remove("o_we_flip_x", "o_we_flip_y");

        shapeContainerEl.classList.toggle("o_we_animated", animated === "true");

        // We need to check if the colors are the default ones because since we
        // do not apply a shape by default anymore, "getDefaultColors" might
        // return an empty object if its the first time a shape is added.
        const defaultColors = getDefaultColors(editingElement);
        const areCustomColors =
            Boolean(colors) &&
            !Object.entries(colors).every(
                ([colorName, colorValue]) =>
                    colorValue.toLowerCase() === defaultColors[colorName]?.toLowerCase()
            );

        const shouldCustomize =
            areCustomColors || flip.length > 0 || parseFloat(shapeAnimationSpeed) !== 0;

        if (shouldCustomize) {
            // Apply custom image, flip, speed
            shapeContainerEl.style.setProperty(
                "background-image",
                `url("${this.getShapeSrc(editingElement)}")`
            );
            shapeContainerEl.style.backgroundPosition = "";

            if (flip.length) {
                let [xPos, yPos] = getComputedStyle(shapeContainerEl)
                    .backgroundPosition.split(" ")
                    .map(parseFloat);

                xPos = flip.includes("x") ? -xPos + 100 : xPos;
                yPos = flip.includes("y") ? -yPos + 100 : yPos;

                shapeContainerEl.style.backgroundPosition = `${xPos}% ${yPos}%`;
            }
        } else {
            // Let CSS class define the shape
            shapeContainerEl.style.setProperty("background-image", "");
            shapeContainerEl.style.setProperty("background-position", "");
        }

        shapeContainerEl.classList.toggle("o_shape_show_mobile", Boolean(showOnMobile));
    }

    /**
     * Creates and inserts a container for the shape with the right classes.
     *
     * @param {HTMLElement} editingElement - The element to which the shape is attached.
     * @param {string} shape - The shape name used to generate a class.
     * @returns {HTMLElement} The created shape container element.
     */
    createShapeContainer(editingElement, shape) {
        const shapeContainer = this.insertShapeContainer(
            editingElement,
            document.createElement("div")
        );
        editingElement.style.setProperty("position", "relative");
        shapeContainer.className = `o_we_shape o_${shape.replace(/\//g, "_")}`;
        return shapeContainer;
    }
    /**
     * Returns the implicit colors for the currently selected shape.
     *
     * The implicit colors are use upon shape selection. They are computed as:
     * - the default colors
     * - patched with each set of colors of previous siblings shape
     * - patched with the colors of the previously selected shape
     * - patched with the color of the bg color of the snippet next to the
     * connection shape
     * - filtered to only keep the colors involved in the current shape
     *
     * @param {HTMLElement} editingElement
     * @param {String} shapeName identifier of the selected shape.
     * @param {Object} previousColors colors of the shape before its
     * replacement.
     */
    getImplicitColors(editingElement, shapeName, previousColors = {}) {
        const selectedBackgroundUrl = this.getShapeStyleUrl(shapeName);
        const defaultColors = this.getShapeDefaultColors(selectedBackgroundUrl);
        let colors = Object.assign(
            { ...previousColors },
            this.getComputedConnectionsColors(editingElement, shapeName)
        );
        let sibling = editingElement.previousElementSibling;
        while (sibling) {
            colors = Object.assign(this.getShapeData(sibling).colors || {}, colors);
            sibling = sibling.previousElementSibling;
        }
        const defaultKeys = Object.keys(defaultColors);
        colors = Object.assign(defaultColors, colors);
        return pick(colors, ...defaultKeys);
    }
    /**
     * Returns the default colors for the a shape in the selector.
     *
     * @param {String} selectedBackgroundUrl
     */
    getShapeDefaultColors(selectedBackgroundUrl) {
        const shapeSrc = selectedBackgroundUrl && getBgImageURLFromURL(selectedBackgroundUrl);
        const url = new URL(shapeSrc, window.location.origin);
        return Object.fromEntries(url.searchParams.entries().filter(([key]) => key !== "flip"));
    }
    /**
     * Retrieves current shape data from the target's dataset.
     *
     * @param {HTMLElement} editingElement the target on which to read the shape
     * data.
     */
    getShapeData(editingElement) {
        const defaultData = {
            shape: "",
            colors: getDefaultColors(editingElement),
            flip: [],
            showOnMobile: false,
            shapeAnimationSpeed: "0",
        };
        const json = editingElement.dataset.oeShapeData;
        if (json) {
            Object.assign(defaultData, JSON.parse(json.replace(/'/g, '"')));
            // Compatibility with old shapes.
            defaultData.shape = defaultData.shape.replace("web_editor", "html_builder");
        }
        return defaultData;
    }
    /**
     * Returns the src of the shape corresponding to the current parameters.
     *
     * @param {HTMLElement} editingElement
     */
    getShapeSrc(editingElement) {
        const { shape, colors, flip, shapeAnimationSpeed } = this.getShapeData(editingElement);
        if (!shape) {
            return "";
        }
        const searchParams = Object.entries(colors).map(([colorName, colorValue]) => {
            const encodedCol = encodeURIComponent(colorValue);
            return `${colorName}=${encodedCol}`;
        });
        if (flip.length) {
            searchParams.push(`flip=${encodeURIComponent(flip.sort().join(""))}`);
        }
        if (Number(shapeAnimationSpeed)) {
            searchParams.push(`shapeAnimationSpeed=${encodeURIComponent(shapeAnimationSpeed)}`);
        }
        return `/html_editor/shape/${encodeURIComponent(shape)}.svg?${searchParams.join("&")}`;
    }
    /**
     *
     * @param {String} shapeId
     */
    getShapeStyleUrl(shapeId) {
        const shapeClassName = `o_${shapeId.replace(/\//g, "_")}`;
        // Match current palette
        return this.shapeBackgroundImagePerClass[`.o_we_shape.${shapeClassName}`];
    }
    /**
     * Inserts or removes the given container at the right position in the
     * document.
     *
     * @param {HTMLElement} editingElement
     * @param {HTMLElement} newContainer container to insert, null to remove
     */
    insertShapeContainer(editingElement, newContainer) {
        const shapeContainerEl = editingElement.querySelector(":scope > .o_we_shape");
        if (shapeContainerEl) {
            this.removeShapeEl(shapeContainerEl);
        }
        if (newContainer) {
            let preShapeLayerEl;
            for (const fn of this.getResource("background_shape_target_providers")) {
                preShapeLayerEl = fn(editingElement);
                if (preShapeLayerEl) {
                    break;
                }
            }
            if (preShapeLayerEl) {
                preShapeLayerEl.insertAdjacentElement("afterend", newContainer);
            } else {
                editingElement.prepend(newContainer);
            }
        }
        return newContainer;
    }
    /**
     * Overwrites shape properties with the specified data.
     *
     * @param {HTMLElement} editingElement
     * @param {Object} newData an object with the new data
     */
    markShape(editingElement, newData) {
        const defaultColors = getDefaultColors(editingElement);
        const shapeData = Object.assign(this.getShapeData(editingElement), newData);
        const areColorsDefault = Object.entries(shapeData.colors).every(
            ([colorName, colorValue]) =>
                defaultColors[colorName] &&
                colorValue.toLowerCase() === defaultColors[colorName].toLowerCase()
        );
        if (areColorsDefault) {
            delete shapeData.colors;
        }
        if (!shapeData.shape) {
            delete editingElement.dataset.oeShapeData;
        } else {
            editingElement.dataset.oeShapeData = JSON.stringify(shapeData);
        }
    }
    /**
     *
     * @param {HTMLElement} shapeEl
     */
    removeShapeEl(shapeEl) {
        shapeEl.remove();
    }
    getBackgroundShapeGroups() {
        return backgroundShapesDefinition;
    }
    getBackgroundShapes() {
        if (!this.backgroundShapesById) {
            const entries = Object.values(this.getBackgroundShapeGroups())
                .map((x) =>
                    Object.values(x.subgroups)
                        .map((x) => Object.entries(x.shapes))
                        .flat()
                )
                .flat();
            this.backgroundShapesById = Object.fromEntries(entries);
        }
        return this.backgroundShapesById;
    }
    /**
     * Returns the actual background visible for an element.
     *
     * @param {HTMLElement} curEl
     */
    getEffectiveBackgroundColor(curEl) {
        while (curEl) {
            const bgColor = getComputedStyle(curEl).backgroundColor;
            if (bgColor !== "rgba(0, 0, 0, 0)" && bgColor !== "transparent") {
                return rgbToHex(bgColor).toLowerCase();
            }
            curEl = curEl.parentElement;
        }
        return "#ffffff";
    }
    /**
     * Returns the computed colors for the currently selected Connections shape.
     *
     * The color is computed based on the bgcolor of the next snippet or on the
     * bgcolor of the previous if the shape flip on Y.
     *
     * @private
     * @param {HTMLElement} editingElement Element for which the color has to be
     * computed.
     * @param {String} shapeName identifier of the selected shape.
     */
    getComputedConnectionsColors(editingElement, shapeName) {
        if (!shapeName.includes("html_builder/Connections/")) {
            return {};
        }
        const selectedBackgroundUrl = this.getShapeStyleUrl(shapeName);
        const defaultColors = this.getShapeDefaultColors(selectedBackgroundUrl);
        const defaultKey = Object.keys(defaultColors)[0];
        const targetRect = editingElement.getBoundingClientRect();
        const shapeData = this.getShapeData(editingElement);
        const x = targetRect.left + targetRect.width / 2;
        const y = shapeData.flip.includes("y") ? targetRect.top - 1 : targetRect.bottom + 1;
        const neighborEl = this.getBackgroundElementFromPoint(x, y);
        const neighborElHexColor = rgbToHex(getComputedStyle(neighborEl).backgroundColor);
        const curBgHexColor = this.getEffectiveBackgroundColor(editingElement);

        return {
            [defaultKey]:
                curBgHexColor !== neighborElHexColor
                    ? neighborElHexColor
                    : this.getContrastingColor(neighborElHexColor),
        };
    }
    /**
     * Compute the luminance of a color.
     *
     * @private
     */
    getLuminance(color) {
        const hexColor = rgbToHex(color);
        const r = parseInt(hexColor.slice(1, 3), 16);
        const g = parseInt(hexColor.slice(3, 5), 16);
        const b = parseInt(hexColor.slice(5), 16);
        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    }
    /**
     * Return the color of the current theme with the most contrast compared to
     * the given color.
     *
     * @private
     */
    getContrastingColor(baseColor) {
        const baseLuminance = this.getLuminance(baseColor);

        const htmlStyle = getHtmlStyle(this.document);
        const colors = ["o-color-1", "o-color-2", "o-color-3", "o-color-4", "o-color-5"];
        const luminances = colors.map((color) => {
            const colorValue = getCSSVariableValue(color, htmlStyle);
            return { color, luminance: this.getLuminance(colorValue) };
        });

        let bestContrast;
        let maxDifference = 0;

        for (const { color, luminance } of luminances) {
            const difference = Math.abs(baseLuminance - luminance);
            if (difference > maxDifference) {
                maxDifference = difference;
                bestContrast = color;
            }
        }

        return getCSSVariableValue(bestContrast, htmlStyle).toLowerCase();
    }
    /**
     * Returns the elements stacked at the given point.
     *
     * Note on coordinates:
     *  - clientX / clientY are viewport (client) coordinates, suitable for
     *    elementsFromPoint() and elementFromPoint().
     *  - documentX / documentY are coordinates relative to the full document
     *    (client + current scroll offsets).
     *
     * If clientX/clientY are outside the viewport, elementsFromPoint cannot be
     * used and we fallback to scanning elements in the document to find those
     * whose bounding rect contains the document coordinates.
     *
     * @private
     * @param {Number} clientX X coordinate relative to the viewport (can be
     * negative).
     * @param {Number} clientY Y coordinate relative to the viewport (can be
     * negative).
     * @returns {HTMLElement[]} Array of elements under the point, top-most
     * first.
     */
    getElementsFromPoint(clientX, clientY) {
        const iframeDoc = this.editable.ownerDocument;
        const iframeWin = iframeDoc.defaultView;
        const documentX = iframeWin.pageXOffset + clientX;
        const documentY = iframeWin.pageYOffset + clientY;
        let elements;
        if (
            clientX >= 0 &&
            clientY >= 0 &&
            clientX <= iframeWin.innerWidth &&
            clientY <= iframeWin.innerHeight
        ) {
            elements = iframeDoc.elementsFromPoint(clientX, clientY);
        } else {
            // If the points is out of the viewport, we can't get the elements
            // with elementsFromPoint so we need to check every element on the
            // page to test if it intersect with the point. The Treewalker
            // improve this logic by avoiding to check children of an element
            // that is not intersecting (compared to a querySelectorAll)
            // This can probably be improved
            elements = [];
            const walker = iframeDoc.createTreeWalker(iframeDoc.body, NodeFilter.SHOW_ELEMENT, {
                acceptNode: (node) => {
                    const rect = node.getBoundingClientRect();
                    const absoluteLeft = iframeWin.pageXOffset + rect.left;
                    const absoluteTop = iframeWin.pageYOffset + rect.top;
                    const absoluteRight = absoluteLeft + rect.width;
                    const absoluteBottom = absoluteTop + rect.height;
                    if (
                        documentX >= absoluteLeft &&
                        documentX <= absoluteRight &&
                        documentY >= absoluteTop &&
                        documentY <= absoluteBottom
                    ) {
                        elements.push(node);
                        return NodeFilter.FILTER_ACCEPT;
                    }
                    return NodeFilter.FILTER_REJECT;
                },
            });
            while (walker.nextNode()) {
                // The walker goes through each node
            }
            elements.reverse();
        }

        // Remove header overlays if necessary (use documentY which is absolute)
        // Or add it if the header is detached from the top of the page
        const header = iframeDoc.querySelector("header");
        if (header) {
            const headerHeight = header.offsetHeight;
            const isHeaderSidebar = header.classList.contains("o_header_sidebar");
            if (documentY > headerHeight || isHeaderSidebar) {
                elements = elements.filter((el) => !el.closest("header"));
            } else if (documentY < headerHeight && !isHeaderSidebar) {
                if (!elements.includes(header)) {
                    elements.unshift(header.querySelector("nav"));
                }
            }
        }

        const wrapwrapEl = iframeDoc.querySelector("#wrapwrap");
        if (wrapwrapEl && wrapwrapEl.classList.contains("o_footer_effect_enable")) {
            const footer = iframeDoc.querySelector("footer");
            const main = iframeDoc.querySelector("main");
            const mainRect = main.getBoundingClientRect();
            const mainBottom = iframeWin.pageYOffset + mainRect.bottom;
            const isJustBelowMain = Math.abs(documentY - mainBottom) <= 2;

            if (isJustBelowMain) {
                elements.unshift(footer);
            } else if (!isJustBelowMain) {
                elements = elements.filter((el) => !el.closest("footer"));
            }
        }
        return elements;
    }
    /**
     * Returns the first element at the given point that has a non-transparent
     * background color, after applying blacklist filters.
     *
     * If no suitable element is found under the point, the <body> element is
     * returned as a fallback because it's not selected by the
     * elementsFromPoints method but always has a background, visible behind
     * snippet without background.
     *
     * @private
     * @param {HTMLElement} editingElement Reference element used to obtain the
     * document.
     * @param {number} clientX X coordinate relative to the viewport.
     * @param {number} clientY Y coordinate relative to the viewport.
     * @returns {HTMLElement} The first visible background element under the
     * point, or <body> if none matches.
     */
    getBackgroundElementFromPoint(clientX, clientY) {
        const elements = this.getElementsFromPoint(clientX, clientY);
        const element = elements.find(
            (el) =>
                (el.closest("[data-snippet]") || el.closest("header") || el.closest("footer")) &&
                !getComputedStyle(el).backgroundColor.includes("rgba(0, 0, 0, 0)")
        );
        return element || this.editable.ownerDocument.querySelector("body");
    }
}

class BaseAnimationAction extends BuilderAction {
    static id = "baseAnimation";
    static dependencies = ["backgroundShapeOption"];
    setup() {
        this.applyShape = this.dependencies.backgroundShapeOption.applyShape;
        this.getShapeData = this.dependencies.backgroundShapeOption.getShapeData;
        this.getImplicitColors = this.dependencies.backgroundShapeOption.getImplicitColors;
        this.getBackgroundShapes = this.dependencies.backgroundShapeOption.getBackgroundShapes;
        this.createShapeContainer = this.dependencies.backgroundShapeOption.createShapeContainer;
    }
}
class SetBackgroundShapeAction extends BaseAnimationAction {
    static id = "setBackgroundShape";
    apply({ editingElement, params, value }) {
        params = params || {};
        const shapeData = this.getShapeData(editingElement);
        const applyShapeParams = {
            shape: value,
            colors: this.getImplicitColors(editingElement, value, shapeData.colors),
            flip: shapeData.flip,
            animated: params.animated,
            shapeAnimationSpeed: shapeData.shapeAnimationSpeed,
        };
        this.applyShape(editingElement, () => applyShapeParams);
    }
    isApplied({ editingElement, value }) {
        const currentShapeApplied = this.getShapeData(editingElement).shape;
        return currentShapeApplied === value;
    }
}
class ShowOnMobileAction extends BaseAnimationAction {
    static id = "showOnMobile";
    apply({ editingElement }) {
        this.applyShape(editingElement, () => ({
            showOnMobile: false,
        }));
    }
    clean({ editingElement }) {
        this.applyShape(editingElement, () => ({
            showOnMobile: true,
        }));
    }
    isApplied({ editingElement }) {
        return !this.getShapeData(editingElement).showOnMobile;
    }
}
class FlipShapeAction extends BaseAnimationAction {
    static id = "flipShape";
    apply({ editingElement, params: { mainParam: axis } }) {
        let { shape, flip, colors } = this.getShapeData(editingElement);
        this.applyShape(editingElement, () => {
            flip = new Set(flip);
            flip.add(axis);
            return { flip: [...flip] };
        });
        if (axis === "y") {
            this.applyShape(editingElement, () => ({
                colors: this.getImplicitColors(editingElement, shape, colors),
            }));
        }
    }
    clean({ editingElement, params: { mainParam: axis } }) {
        let { shape, flip, colors } = this.getShapeData(editingElement);
        this.applyShape(editingElement, () => {
            flip = new Set(flip);
            flip.delete(axis);
            return { flip: [...flip] };
        });
        if (axis === "y") {
            this.applyShape(editingElement, () => ({
                colors: this.getImplicitColors(editingElement, shape, colors),
            }));
        }
    }
    isApplied({ editingElement, params: { mainParam: axis } }) {
        // Compat: flip classes are no longer used but may be
        // present in client db.
        const selector = `.o_we_flip_${axis}`;
        const hasFlipClass = !!editingElement.querySelector(`:scope > .o_we_shape${selector}`);
        return hasFlipClass || this.getShapeData(editingElement).flip.includes(axis);
    }
}
class SetBgAnimationSpeedAction extends BaseAnimationAction {
    static id = "setBgAnimationSpeed";
    apply({ editingElement, value }) {
        this.applyShape(editingElement, () => ({
            shapeAnimationSpeed: value,
        }));
    }
    getValue({ editingElement }) {
        return this.getShapeData(editingElement).shapeAnimationSpeed;
    }
}
class BackgroundShapeColorAction extends BaseAnimationAction {
    static id = "backgroundShapeColor";
    getValue({ editingElement, params: { mainParam: colorName } }) {
        // TODO check if it works when the colorpicker is
        // implemented.
        const { shape, colors: customColors } = this.getShapeData(editingElement);
        const colors = Object.assign(getDefaultColors(editingElement), customColors);
        const color = shape && colors[colorName];
        return (color && normalizeColor(color, getHtmlStyle(this.document))) || "";
    }
    apply({ editingElement, params: { mainParam: colorName }, value }) {
        this.applyShape(editingElement, () => {
            value = getValueFromVar(value);
            const { colors: previousColors } = this.getShapeData(editingElement);
            const newColor = value || getDefaultColors(editingElement)[colorName];
            const newColors = Object.assign(previousColors, { [colorName]: newColor });
            return { colors: newColors };
        });
    }
}

registry
    .category("builder-plugins")
    .add(BackgroundShapeOptionPlugin.id, BackgroundShapeOptionPlugin);
