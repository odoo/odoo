import { defaultBuilderComponents } from "../../core/default_builder_components";
import { BackgroundShapeComponent } from "@html_builder/plugins/background_option/background_shape_component";
import { getBgImageURLFromEl, getBgImageURLFromURL } from "@html_builder/utils/utils_css";
import { Plugin } from "@html_editor/plugin";
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";

class BackgroundOptionPlugin extends Plugin {
    static id = "BackgroundOption";
    resources = {
        builder_actions: this.getActions(),
        builder_options: [
            {
                selector: "section",
                OptionComponent: BackgroundComponent,
                props: {
                    // TODO: to handle
                    // withColors: true,
                    // withImages: true,
                    // // todo: handle with_videos
                    // withShapes: true,
                    // withGradient: true,
                    // withColorCombinations: true,
                    getShapeData: this.getShapeData.bind(this),
                    getShapeStyleUrl: this.getShapeStyleUrl.bind(this),
                },
            },
        ],
    };
    getActions() {
        return {
            applyShape: {
                apply: ({ editingElement, param }) => {
                    const shapeData = this.getShapeData(editingElement);
                    const applyShapeParams = {
                        shape: param.shape,
                        colors: this.getImplicitColors(
                            editingElement,
                            shapeData.colors,
                            param.shape
                        ),
                        flip: [],
                        animated: param.animated,
                        shapeAnimationSpeed: shapeData.shapeAnimationSpeed,
                    };
                    this.applyShape(editingElement, () => applyShapeParams);
                },
                isApplied: ({ editingElement, param }) => {
                    const currentShapeApplied = this.getShapeData(editingElement).shape;
                    return currentShapeApplied === param.shape;
                },
            },
        };
    }

    setup() {
        this.shapeBackgroundImagePerClass = {};
        for (const styleSheet of this.document.styleSheets) {
            if (styleSheet.href && new URL(styleSheet.href).host !== location.host) {
                // In some browsers, if a stylesheet is loaded from a different domain
                // accessing cssRules results in a SecurityError.
                continue;
            }
            for (const rule of [...styleSheet.cssRules]) {
                if (rule.selectorText && rule.selectorText.startsWith(".o_we_shape.")) {
                    this.shapeBackgroundImagePerClass[rule.selectorText] =
                        rule.style.backgroundImage;
                }
            }
        }
    }

    /**
     * Handles everything related to saving state before preview and restoring
     * it after a preview or locking in the changes when not in preview.
     *
     * @param {HTMLElement} editingElement
     * @param {Function} computeShapeData function to compute the new shape data.
     */
    applyShape(editingElement, computeShapeData) {
        const oeShapeData = editingElement.dataset.oeShapeData;
        const curShapeData = oeShapeData ? JSON.parse(oeShapeData) : {};
        const newShapeData = computeShapeData();
        const { shape: curShape } = curShapeData;
        const changedShape = newShapeData.shape !== curShape;
        this.markShape(editingElement, newShapeData);
        if (changedShape) {
            // TODO: handle the correct number of colorpicker
        }

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
        // When changing shape we want to reset the shape container (for transparency color)
        if (changedShape) {
            shapeContainerEl = this.createShapeContainer(editingElement, shape);
        }
        // Compat: remove old flip classes as flipping is now done inside the svg
        shapeContainerEl.classList.remove("o_we_flip_x", "o_we_flip_y");

        shapeContainerEl.classList.toggle("o_we_animated", animated === "true");
        if (colors || flip.length || parseFloat(shapeAnimationSpeed) !== 0) {
            // Custom colors/flip/speed, overwrite shape that is set by the class
            shapeContainerEl.style.setProperty(
                "background-image",
                `url("${this.getShapeSrc(editingElement)}")`
            );
            shapeContainerEl.style.backgroundPosition = "";
            if (flip.length) {
                let [xPos, yPos] = getComputedStyle(shapeContainerEl)
                    .backgroundPosition.split(" ")
                    .map((p) => parseFloat(p));
                // -X + 2*Y is a symmetry of X around Y, this is a symmetry around 50%
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
     * Returns the default colors for the currently selected shape.
     *
     * @param {HTMLElement} editingElement the element on which to read the
     * shape data.
     */
    getDefaultColors(editingElement) {
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
     * @param {Object} previousColors colors of the shape before its replacement
     * @param {String} shapeName identifier of the selected shape
     */
    getImplicitColors(editingElement, previousColors, shapeName) {
        const selectedBackgroundUrl = this.getShapeStyleUrl(shapeName);
        const defaultColors = this.getShapeDefaultColors(selectedBackgroundUrl);
        let colors = previousColors || {};
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
            colors: this.getDefaultColors(editingElement),
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
     * @param {String} shapeName
     */
    getShapeStyleUrl(shapeName) {
        const shapeClassName = `o_${shapeName.replace(/\//g, "_")}`;
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
        const defaultColors = this.getDefaultColors(editingElement);
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
}
registry.category("website-plugins").add(BackgroundOptionPlugin.id, BackgroundOptionPlugin);

export class BackgroundComponent extends Component {
    static template = "html_builder.BackgroundComponent";
    static components = { ...defaultBuilderComponents };
    static props = {
        // TODO: to handle
        // withColors: { type: Boolean },
        // withImages: { type: Boolean },
        // withColorCombinations: { type: Boolean },
        // withGradient: { type: Boolean },
        // withShapes: { type: Boolean, optional: true },
        getShapeData: { type: Function },
        getShapeStyleUrl: { type: Function },
    };
    static defaultProps = {
        withShapes: false,
    };
    showBackgroundShapes() {
        this.env.openCustomizeComponent(BackgroundShapeComponent, this.env.getEditingElements(), {
            getShapeStyleUrl: this.props.getShapeStyleUrl.bind(this),
        });
    }
    showBackgroundShapeButton() {
        const editingEl = this.env.getEditingElement();
        return !!this.props.getShapeData(editingEl).shape;
    }
}
