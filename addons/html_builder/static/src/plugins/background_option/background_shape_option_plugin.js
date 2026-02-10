import { getValueFromVar } from "@html_builder/utils/utils";
import { normalizeColor } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { deepCopy, deepMerge, pick } from "@web/core/utils/objects";
import { backgroundShapesDefinition } from "./background_shapes_definition";
import { getDefaultColors } from "./background_shape_option";
import { withSequence } from "@html_editor/utils/resource";
import { getBgImageURLFromURL } from "@html_editor/utils/image";
import { BuilderAction } from "@html_builder/core/builder_action";
import { getHtmlStyle, getCSSVariableValue } from "@html_editor/utils/formatting";
import { rgbToHex, isColorGradient } from "@web/core/utils/colors";
import { isVisible } from "@web/core/utils/ui";
import { selectElements } from "@html_editor/utils/dom_traversal";

/**
 * @typedef {Object.<string, {
 *   label?: string,
 *   subgroups: Object.<string, {
 *     label?: string,
 *     shapes: Object.<string, {
 *       selectLabel?: string,
 *       animated?: boolean,
 *     }>,
 *   }>,
 * }>} BackgroundShapeGroups
 * @typedef {((shapeGroups: BackgroundShapeGroups) => BackgroundShapeGroups | void)[]} background_shape_groups_providers
 * @typedef {((editingElement: HTMLElement) => HTMLElement)[]} background_shape_target_providers
 */

export class BackgroundShapeOptionPlugin extends Plugin {
    static id = "backgroundShapeOption";
    static dependencies = ["visibility"];
    /** @type {import("plugins").BuilderResources} */
    resources = {
        builder_actions: {
            SetBackgroundShapeAction,
            ShowOnMobileAction,
            FlipShapeAction,
            SetBgAnimationSpeedAction,
            BackgroundShapeColorAction,
            RangeSelectionAction,
        },
        background_shape_groups_providers: withSequence(0, () =>
            deepCopy(backgroundShapesDefinition)
        ),
        background_shape_target_providers: withSequence(5, (editingElement) =>
            editingElement.querySelector(":scope > .o_we_bg_filter")
        ),
        content_not_editable_selectors: ".o_we_shape",
        system_node_selectors: ".o_we_shape",
        // Handle the update of background shape colors as we want connection
        // color to be updated thanks to adjacent snippet background color. This
        // should normally have been done at the normalize. However, as snippets
        // can be hide in desktop/mobile, there can be some inconsistent state
        // when toggling desktop/mobile view. As we do not want to have a
        // background color shape recomputation of unwanted snippets, the
        // recomputation is done at the different handlers.
        on_element_dropped_over_handlers: ({ droppedEl, dragState }) =>
            this.handleElementMoved({ movedEl: droppedEl, dragState }),
        on_element_dropped_near_handlers: ({ droppedEl, dragState }) =>
            this.handleElementMoved({ movedEl: droppedEl, dragState }),
        on_bg_color_updated_handlers: this.handleBgColorUpdated.bind(this),
        on_element_arrow_moved_handlers: this.handleElementMoved.bind(this),
        on_shape_flipped_handlers: this.handleShapeFlipped.bind(this),
        on_removed_handlers: ({ removedEl, originPreviousEl, originNextEl }) =>
            this.handleElementMoved({
                movedEl: removedEl,
                dragState: { originPreviousEl, originNextEl },
            }),
        on_snippet_dropped_handlers: ({ snippetEl }) => this.handleBgColorUpdated(snippetEl),
        on_cloned_handlers: ({ cloneEl }) => this.handleBgColorUpdated(cloneEl),
    };
    static shared = [
        "getShapeStyleUrl",
        "getShapeData",
        "getBackgroundShapeGroups",
        "getBackgroundShapes",
        "getImplicitColors",
        "applyShape",
        "createShapeContainer",
        "getComputedConnectionsColors",
        "handleBgColorUpdated",
        "isShapeEligibleForComputation",
        "getShapeSrc",
        "getShapeStylePosition",
    ];
    setup() {
        // TODO: update shapeStyles if a stylesheet value changes.
        this.shapeStyles = {};
        const keywordMap = { top: 0, left: 0, center: 50, bottom: 100, right: 100 };
        for (const styleSheet of this.document.styleSheets) {
            if (styleSheet.href && new URL(styleSheet.href).host !== location.host) {
                // In some browsers, if a stylesheet is loaded from a different
                // domain accessing cssRules results in a SecurityError.
                continue;
            }
            for (const rule of [...styleSheet.cssRules]) {
                if (rule.selectorText && rule.selectorText.startsWith(".o_we_shape.")) {
                    const bgPositions = rule.style.backgroundPosition.split(" ");
                    this.shapeStyles[rule.selectorText] = {
                        bgImage: rule.style.backgroundImage,
                        bgPosition: bgPositions.map((bgPosition) => keywordMap[bgPosition]),
                    };
                }
            }
        }
        // Flip classes should no longer be used but are still present in some
        // theme snippets.
        const flipEls = [...this.editable.querySelectorAll(".o_we_flip_x, .o_we_flip_y")];
        for (const flipEl of flipEls) {
            this.applyShape(flipEl, () => ({ flip: this.getShapeData(flipEl).flip }));
        }
        // Add the "selectedColor" key on bg shape introduced before the
        // computed background shape color feature.
        for (const bgShapeEl of selectElements(this.editable, "[data-oe-shape-data]")) {
            const shapeData = JSON.parse(bgShapeEl.dataset.oeShapeData.replace(/'/g, '"'));
            if (!Object.hasOwn(shapeData, "selectedColor")) {
                this.markShape(bgShapeEl, { selectedColor: true });
            }
        }
    }
    /**
     * Updates the background color shape when a snippet is moved/removed. The
     * updated background shapes are:
     * - The adjacent background shape to the original location of the snippet.
     * - The adjacent background shape to the new location of the snippet.
     * - The possible background shape of the moved snippet.
     * @param {Object} - movedEl: the moved element
     *                 - dragState: the current drag state
     */
    handleElementMoved({ movedEl, dragState }) {
        if (!movedEl.matches("[data-snippet]")) {
            return;
        }
        const { originNextEl, originPreviousEl } = dragState;
        const neighborShapeEls = this.getNeighborShapeEls(originPreviousEl, originNextEl);
        for (const neighborShapeEl of neighborShapeEls) {
            this.updateConnectionShapeColor(neighborShapeEl);
        }
        if (movedEl.isConnected) {
            this.handleBgColorUpdated(movedEl);
        }
    }
    /**
     * Updates the background color of a flipped shape if necessary.
     * @param {Object} - editingElement: the snippet of which the background
     * shape has been flipped.
     *                 - axis: "x" | "y"
     */
    handleShapeFlipped({ editingElement, axis }) {
        if (!editingElement.matches("[data-snippet]") || axis !== "y") {
            return;
        }
        this.updateConnectionShapeColor(editingElement);
    }
    /**
     * Computes and updates the background color shape of a snippet
     * @param {HTMLElement} editingEl - a snippet on the page.
     */
    updateConnectionShapeColor(editingEl) {
        const { shape, colors } = this.getShapeData(editingEl);
        if (!this.isShapeEligibleForComputation(shape, editingEl)) {
            return;
        }
        const newColors = this.getImplicitColors(editingEl, shape, colors);
        const computedConnectionsColors = this.getComputedConnectionsColors(
            editingEl,
            shape,
            false
        );
        const selectedColor =
            Object.values(computedConnectionsColors)[0].toLowerCase() !==
            Object.values(newColors)[0].toLowerCase();
        this.applyShape(editingEl, () => ({
            colors: newColors,
            selectedColor,
        }));
    }
    /**
     * A shape is eligible to receive a computed color if it is a visible (or
     * not yet existing) "connection" shape applied on a visible non layered
     * snippet.
     * @param {String} shapeName
     * @param {HTMLElement} editingEl
     * @returns {Boolean}
     */
    isShapeEligibleForComputation(shapeName, editingEl) {
        return (
            this.isConnectionShape(shapeName) &&
            editingEl.matches("[data-snippet]") &&
            !editingEl.parentElement.closest("[data-snippet]") &&
            (isVisible(editingEl.querySelector(":scope > .o_we_shape")) ||
                !editingEl.querySelector(":scope > .o_we_shape")) &&
            this.isVisibleSnippet(editingEl)
        );
    }
    isConnectionShape(shapeName) {
        const shapeInfo = this.getBackgroundShapes()[shapeName];
        if (!shapeName || !shapeInfo) {
            return false;
        }
        return shapeInfo.subgroup === "connections";
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
                `url("${this.getShapeSrc(this.getShapeData(editingElement))}")`
            );
            shapeContainerEl.style.backgroundPosition = "";

            if (flip.length) {
                let [xPos, yPos] = getComputedStyle(shapeContainerEl)
                    .backgroundPosition.split(" ")
                    .map(parseFloat);

                [xPos, yPos] = this.computeFlipPos(xPos, yPos, flip);

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
            selectedColor: false,
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
     */
    getShapeSrc({ shape, colors, flip, shapeAnimationSpeed }) {
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
        // Match current palette
        if (!shapeId) {
            return "";
        }
        return this.shapeStyles[this.convertShapeIdForStyleSearch(shapeId)]?.bgImage;
    }
    getShapeStylePosition(shapeId, flip) {
        if (!shapeId) {
            return "";
        }
        const [xPos, yPos] = this.shapeStyles[this.convertShapeIdForStyleSearch(shapeId)]
            ?.bgPosition || [50, 50];
        return this.computeFlipPos(xPos, yPos, flip);
    }
    computeFlipPos(xPos, yPos, flip) {
        if (!flip) {
            return [xPos, yPos];
        }
        const xFlip = flip.includes("x") ? -xPos + 100 : xPos;
        const yFlip = flip.includes("y") ? -yPos + 100 : yPos;
        return [xFlip, yFlip];
    }
    convertShapeIdForStyleSearch(shapeId) {
        return `.o_we_shape.o_${shapeId.replace(/\//g, "_")}`;
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
        if (!this.backgroundShapeGroups) {
            const shapeGroups = {};
            for (const provider of this.getResource("background_shape_groups_providers")) {
                const providedGroups = provider(shapeGroups);
                if (providedGroups) {
                    Object.assign(shapeGroups, deepMerge(shapeGroups, providedGroups));
                }
            }
            this.backgroundShapeGroups = shapeGroups;
        }
        return this.backgroundShapeGroups;
    }
    getBackgroundShapes() {
        if (!this.backgroundShapesById) {
            const entries = Object.values(this.getBackgroundShapeGroups()).flatMap((groupValue) =>
                Object.entries(groupValue.subgroups).flatMap(([subgroupKey, subgroupValue]) =>
                    Object.entries(subgroupValue.shapes).map(([key, value]) => [
                        key,
                        { ...value, subgroup: subgroupKey },
                    ])
                )
            );
            this.backgroundShapesById = Object.fromEntries(entries);
        }
        return this.backgroundShapesById;
    }
    /**
     * Handles a background color change on an element and updates Connections
     * shapes accordingly.
     *
     * @param {HTMLElement} editingElement Element whose background color has
     * changed.
     */
    handleBgColorUpdated(editingElement) {
        if (
            !editingElement.dataset.snippet ||
            editingElement.parentElement.closest("[data-snippet]")
        ) {
            return;
        }
        const neighborShapeEls = this.getNeighborShapeEls(
            editingElement["previousElementSibling"],
            editingElement["nextElementSibling"]
        );
        for (const neighborShapeEl of [...neighborShapeEls, editingElement]) {
            this.updateConnectionShapeColor(neighborShapeEl);
        }
    }
    /**
     * Computes the color of Connections background shape applied on a
     * (non-layered) snippet.
     *
     * The color is computed based on the displayed background color of the
     * adjacent snippet.
     *
     * @param {HTMLElement} editingElement - Element for which the color has to
     * be computed.
     * @param {String} shapeName - Identifier of the selected shape.
     * @param {Boolean} considerSelectedColor - If the `selectedColor`
     * properties has to be taken into account in the computation of the
     * background shape color.
     * @returns {Object} - The computed shape color.
     */
    getComputedConnectionsColors(editingElement, shapeName, considerSelectedColor = true) {
        if (!this.isShapeEligibleForComputation(shapeName, editingElement)) {
            return {};
        }
        const selectedBackgroundUrl = this.getShapeStyleUrl(shapeName);
        const defaultColors = this.getShapeDefaultColors(selectedBackgroundUrl);
        const defaultKey = Object.keys(defaultColors)[0];
        const shapeData = this.getShapeData(editingElement);
        if (considerSelectedColor && shapeData.selectedColor) {
            return {
                [defaultKey]: normalizeColor(
                    Object.values(shapeData.colors)[0],
                    getHtmlStyle(this.document)
                ),
            };
        }
        const neighborEl = this.getAdjacentEl(editingElement);
        const neighborBgColor = neighborEl && getComputedStyle(neighborEl).backgroundColor;
        const hasNeighborTransparency = neighborBgColor?.match(/rgba/);
        const computedHexColor =
            neighborEl &&
            !isColorGradient(getComputedStyle(neighborEl).backgroundImage) &&
            !hasNeighborTransparency
                ? rgbToHex(neighborBgColor)
                : Object.values(defaultColors)[0];
        const curBgHexColor = rgbToHex(getComputedStyle(editingElement).backgroundColor);

        return {
            [defaultKey]:
                curBgHexColor !== computedHexColor
                    ? computedHexColor
                    : this.getContrastingColor(computedHexColor),
        };
    }

    /**
     * Returns the adjacent snippet of a background shape.
     * @param {HTMLElement} editingElement - The snippet that has the background
     * shape.
     * @returns {HTMLElement|undefined} - The adjacent snippet.
     */
    getAdjacentEl(editingElement) {
        const shapeData = this.getShapeData(editingElement);
        const isYFlipped = shapeData.flip.includes("y");
        const elementSibling = isYFlipped ? "previousElementSibling" : "nextElementSibling";
        let siblingEl = editingElement[elementSibling];
        while (siblingEl) {
            if (this.isVisibleSnippet(siblingEl)) {
                return siblingEl;
            }
            siblingEl = siblingEl[elementSibling];
        }
    }
    /**
     * Compute the luminance of a color.
     *
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
     * Returns the neighboring snippets that contains a shape element.
     *
     * @param {HTMLElement | undefined} previousEl The previous element of the
     * snippet.
     * @param {HTMLElement | undefined} nextEl The next element of the snippet.
     * @returns {HTMLElement[]} List of neighboring shape elements.
     */
    getNeighborShapeEls(previousEl, nextEl) {
        const getBgShapedSnippetSiblingEl = (siblingEl, elementSibling) => {
            while (siblingEl) {
                if (this.isVisibleSnippet(siblingEl) && !siblingEl.matches(".oe_drop_clone")) {
                    return siblingEl.dataset.oeShapeData ? siblingEl : null;
                }
                siblingEl = siblingEl[elementSibling];
            }
        };
        const aboveShapeSnippetEl = previousEl
            ? getBgShapedSnippetSiblingEl(previousEl, "previousElementSibling")
            : undefined;
        const underShapeSnippetEl = nextEl
            ? getBgShapedSnippetSiblingEl(nextEl, "nextElementSibling")
            : undefined;
        return [aboveShapeSnippetEl, underShapeSnippetEl].filter(Boolean);
    }
    /**
     * Checks if an element is a snippet that is visible on the page and is not
     * in the invisible panel
     * @param {HTMLElement} el
     * @returns {Boolean}
     */
    isVisibleSnippet(el) {
        const invisibleEls = this.dependencies.visibility.getInvisibleElements();
        return el.matches("[data-snippet]") && isVisible(el) && !invisibleEls.includes(el);
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
        this.isShapeEligibleForComputation =
            this.dependencies.backgroundShapeOption.isShapeEligibleForComputation;
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
        this.applyShape(editingElement, () => {
            const flip = new Set(this.getShapeData(editingElement).flip);
            flip.add(axis);
            return { flip: [...flip] };
        });
        this.dispatchTo("on_shape_flipped_handlers", { editingElement, axis });
    }
    clean({ editingElement, params: { mainParam: axis } }) {
        this.applyShape(editingElement, () => {
            const flip = new Set(this.getShapeData(editingElement).flip);
            flip.delete(axis);
            return { flip: [...flip] };
        });
        this.dispatchTo("on_shape_flipped_handlers", { editingElement, axis });
    }
    isApplied({ editingElement, params: { mainParam: axis } }) {
        // Compat: flip classes are no longer used but may be
        // present in client db.
        const selector = `.o_we_flip_${axis}`;
        const hasFlipClass = !!editingElement.querySelector(`:scope > .o_we_shape${selector}`);
        return hasFlipClass || this.getShapeData(editingElement).flip.includes(axis);
    }
}
class RangeSelectionAction extends BaseAnimationAction {
    static id = "rangeSelection";
    apply({ editingElement, params: { mainParam: values }, value }) {
        for (const c of values) {
            editingElement.classList.remove(c);
        }
        if (value) {
            editingElement.classList.add(value);
        }
    }
    getValue({ editingElement, params: { mainParam: values } }) {
        for (const c of values) {
            if (editingElement.classList.contains(c)) {
                return values.indexOf(c) + 1;
            }
        }
        return 0;
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
            const { shape } = this.getShapeData(editingElement);
            if (!this.isShapeEligibleForComputation(shape, editingElement)) {
                return { colors: newColors, selectedColor: true };
            }
            const computedConnectionsColors =
                this.dependencies.backgroundShapeOption.getComputedConnectionsColors(
                    editingElement,
                    shape,
                    false
                );
            let selectedColor = true;
            if (Object.values(computedConnectionsColors).length) {
                selectedColor =
                    normalizeColor(newColor, getHtmlStyle(this.document)).toLowerCase() !==
                    Object.values(computedConnectionsColors)[0].toLowerCase();
            }
            return { colors: newColors, selectedColor };
        });
    }
}

registry
    .category("builder-plugins")
    .add(BackgroundShapeOptionPlugin.id, BackgroundShapeOptionPlugin);
