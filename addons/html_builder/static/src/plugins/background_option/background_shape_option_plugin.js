import { getValueFromVar, isMobileView } from "@html_builder/utils/utils";
import { getBgImageURLFromURL, normalizeColor } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { backgroundShapesDefinition } from "./background_shapes_definition";
import { ShapeSelector } from "../shape/shape_selector";
import { getDefaultColors } from "./background_shape_option";

class BackgroundShapeOptionPlugin extends Plugin {
    static id = "backgroundShapeOption";
    static dependencies = ["customizeTab"];
    resources = {
        builder_actions: this.getActions(),
    };
    static shared = [
        "getShapeStyleUrl",
        "getShapeData",
        "showBackgroundShapes",
        "getBackgroundShapes",
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
    getActions() {
        return {
            setBackgroundShape: {
                apply: ({ editingElement, param, value }) => {
                    param = param || {};
                    const shapeData = this.getShapeData(editingElement);
                    const applyShapeParams = {
                        shape: value,
                        colors: this.getImplicitColors(editingElement, value, shapeData.colors),
                        flip: [],
                        animated: param.animated,
                        shapeAnimationSpeed: shapeData.shapeAnimationSpeed,
                    };
                    this.applyShape(editingElement, () => applyShapeParams);
                },
                isApplied: ({ editingElement, value }) => {
                    const currentShapeApplied = this.getShapeData(editingElement).shape;
                    return currentShapeApplied === value;
                },
            },
            toggleBgShape: {
                apply: ({ editingElement }) => {
                    const previousSibling = editingElement.previousElementSibling;
                    let shapeToSelect;
                    const allPossiblesShapesUrl = Object.keys(this.getBackgroundShapes());
                    if (previousSibling) {
                        const previousShape = this.getShapeData(previousSibling).shape;
                        shapeToSelect = allPossiblesShapesUrl.find(
                            (shape, i) => allPossiblesShapesUrl[i - 1] === previousShape
                        );
                    }
                    // If there is no previous sibling, if the previous sibling
                    // had the last shape selected or if the previous shape
                    // could not be found in the possible shapes, default to the
                    // first shape. ([0] being no shapes selected.)
                    if (!shapeToSelect) {
                        shapeToSelect = allPossiblesShapesUrl[1];
                    }
                    // Only show on mobile by default if toggled from mobile
                    // view.
                    const showOnMobile = isMobileView(editingElement);
                    this.createShapeContainer(editingElement, shapeToSelect);
                    const applyShapeParams = {
                        shape: shapeToSelect,
                        colors: this.getImplicitColors(editingElement, shapeToSelect),
                        showOnMobile,
                    };
                    this.applyShape(editingElement, () => applyShapeParams);
                    this.showBackgroundShapes([editingElement]);
                },
                clean: ({ editingElement }) => {
                    this.applyShape(editingElement, () => ({ shape: "" }));
                },
                isApplied: ({ editingElement }) => !!this.getShapeData(editingElement).shape,
            },
            showOnMobile: {
                apply: ({ editingElement }) => {
                    this.applyShape(editingElement, () => ({
                        showOnMobile: false,
                    }));
                },
                clean: ({ editingElement }) => {
                    this.applyShape(editingElement, () => ({
                        showOnMobile: true,
                    }));
                },
                isApplied: ({ editingElement }) => !this.getShapeData(editingElement).showOnMobile,
            },
            flipShape: {
                apply: ({ editingElement, param: { mainParam: axis } }) => {
                    this.applyShape(editingElement, () => {
                        const flip = new Set(this.getShapeData(editingElement).flip);
                        flip.add(axis);
                        return { flip: [...flip] };
                    });
                },
                clean: ({ editingElement, param: { mainParam: axis } }) => {
                    this.applyShape(editingElement, () => {
                        const flip = new Set(this.getShapeData(editingElement).flip);
                        flip.delete(axis);
                        return { flip: [...flip] };
                    });
                },
                isApplied: ({ editingElement, param: { mainParam: axis } }) => {
                    // Compat: flip classes are no longer used but may be
                    // present in client db.
                    const selector = `.o_we_flip_${axis}`;
                    const hasFlipClass = !!editingElement.querySelector(
                        `:scope > .o_we_shape${selector}`
                    );
                    return hasFlipClass || this.getShapeData(editingElement).flip.includes(axis);
                },
            },
            setBgAnimationSpeed: {
                apply: ({ editingElement, value }) => {
                    this.applyShape(editingElement, () => ({ shapeAnimationSpeed: value }));
                },
                getValue: ({ editingElement }) =>
                    this.getShapeData(editingElement).shapeAnimationSpeed,
            },
            backgroundShapeColor: {
                getValue: ({ editingElement, param: { mainParam: colorName } }) => {
                    // TODO check if it works when the colorpicker is
                    // implemented.
                    const { shape, colors: customColors } = this.getShapeData(editingElement);
                    const colors = Object.assign(getDefaultColors(editingElement), customColors);
                    const color = shape && colors[colorName];
                    return (color && normalizeColor(color)) || "";
                },
                apply: ({ editingElement, param: { mainParam: colorName }, value }) => {
                    this.applyShape(editingElement, () => {
                        value = getValueFromVar(value);
                        const { colors: previousColors } = this.getShapeData(editingElement);
                        const newColor = value || getDefaultColors(editingElement)[colorName];
                        const newColors = Object.assign(previousColors, { [colorName]: newColor });
                        return { colors: newColors };
                    });
                },
            },
        };
    }
    /**
     * Handles everything related to saving state before preview and restoring
     * it after a preview or locking in the changes when not in preview.
     *
     * @param {HTMLElement} editingElement
     * @param {Function} computeShapeData function to compute the new shape
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
        // When changing shape we want to reset the shape container (for
        // transparency color).
        if (changedShape) {
            shapeContainerEl = this.createShapeContainer(editingElement, shape);
        }
        // Compat: remove old flip classes as flipping is now done inside the
        // svg.
        shapeContainerEl.classList.remove("o_we_flip_x", "o_we_flip_y");

        shapeContainerEl.classList.toggle("o_we_animated", animated === "true");
        if (colors || flip.length || parseFloat(shapeAnimationSpeed) !== 0) {
            // Custom colors/flip/speed, overwrite shape that is set by the
            // class.
            shapeContainerEl.style.setProperty(
                "background-image",
                `url("${this.getShapeSrc(editingElement)}")`
            );
            shapeContainerEl.style.backgroundPosition = "";
            if (flip.length) {
                let [xPos, yPos] = getComputedStyle(shapeContainerEl)
                    .backgroundPosition.split(" ")
                    .map((p) => parseFloat(p));
                // -X + 2*Y is a symmetry of X around Y, this is a symmetry
                // around 50%.
                xPos = flip.includes("x") ? -xPos + 100 : xPos;
                yPos = flip.includes("y") ? -yPos + 100 : yPos;
                shapeContainerEl.style.backgroundPosition = `${xPos}% ${yPos}%`;
            }
        } else {
            // Remove custom bg image and let the shape class set the bg shape
            shapeContainerEl.style.setProperty("background-image", "");
            shapeContainerEl.style.setProperty("background-position", "");
        }
        shapeContainerEl.classList.toggle("o_shape_show_mobile", !!showOnMobile);
    }

    /**
     * Creates and inserts a container for the shape with the right classes.
     *
     * @param {HTMLElement} editingElement
     * @param {String} shape the shape name for which to create a container
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
        let colors = previousColors;
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
     *
     * @param {HTMLElement} editingElement
     */
    getLastPreShapeLayerElement(editingElement) {
        return editingElement.querySelector(":scope > .o_we_bg_filter");
    }
    /**
     * Returns the default colors for the a shape in the selector.
     *
     * @param {String} selectedBackgroundUrl
     */
    getShapeDefaultColors(selectedBackgroundUrl) {
        const shapeSrc = selectedBackgroundUrl && getBgImageURLFromURL(selectedBackgroundUrl);
        const url = new URL(shapeSrc, window.location.origin);
        return Object.fromEntries(url.searchParams.entries());
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
        return json ? Object.assign(defaultData, JSON.parse(json.replace(/'/g, '"'))) : defaultData;
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
        return `/web_editor/shape/${encodeURIComponent(shape)}.svg?${searchParams.join("&")}`;
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
            const preShapeLayerElement = this.getLastPreShapeLayerElement(editingElement);
            if (preShapeLayerElement) {
                preShapeLayerElement.insertAdjacentElement("afterend", newContainer);
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
    showBackgroundShapes(editingElements) {
        this.dependencies.customizeTab.openCustomizeComponent(ShapeSelector, editingElements, {
            shapeActionId: "setBackgroundShape",
            buttonWrapperClassName: "button_shape",
            shapeGroups: this.getBackgroundShapeGroups(),
            imgThroughDiv: true,
            getShapeUrl: this.getShapeStyleUrl.bind(this),
        });
    }
    getBackgroundShapeGroups() {
        return backgroundShapesDefinition;
    }
    getBackgroundShapes() {
        const entries = Object.values(this.getBackgroundShapeGroups())
            .map((x) =>
                Object.values(x.subgroups)
                    .map((x) => Object.entries(x.shapes))
                    .flat()
            )
            .flat();
        return Object.fromEntries(entries);
    }
}

registry
    .category("website-plugins")
    .add(BackgroundShapeOptionPlugin.id, BackgroundShapeOptionPlugin);
