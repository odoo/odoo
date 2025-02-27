import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { DEFAULT_PALETTE } from "@html_editor/utils/color";
import { isCSSColor } from "@web/core/utils/colors";
import { getCSSVariableValue } from "@html_builder/utils/utils_css";
import { getImageMimetype, getShapeURL } from "./image_helpers";
import {
    applyModifications,
    createDataURL,
    loadImage,
    loadImageInfo,
} from "@html_editor/utils/image_processing";
import { getValueFromVar } from "@html_builder/utils/utils";
import { imageShapeDefinitions } from "./image_shapes_definition";

// Regex definitions to apply speed modification in SVG files
// Note : These regex patterns are duplicated on the server side for
// background images that are part of a CSS rule "background-image: ...". The
// client-side regex patterns are used for images that are part of an
// "src" attribute with a base64 encoded svg in the <img> tag. Perhaps we should
// consider finding a solution to define them only once? The issue is that the
// regex patterns in Python are slightly different from those in JavaScript.
// See : controllers/main.py
const CSS_ANIMATION_RULE_REGEX =
    /(?<declaration>animation(?:-duration)?: .*?)(?<value>(?:\d+(?:\.\d+)?)|(?:\.\d+))(?<unit>ms|s)(?<separator>\s|;|"|$)/gm;
const SVG_DUR_TIMECOUNT_VAL_REGEX =
    /(?<attribute_name>\sdur="\s*)(?<value>(?:\d+(?:\.\d+)?)|(?:\.\d+))(?<unit>h|min|ms|s)?\s*"/gm;
const CSS_ANIMATION_RATIO_REGEX = /(--animation_ratio: (?<ratio>\d*(\.\d+)?));/m;

class ImageShapeOptionPlugin extends Plugin {
    static id = "imageShapeOption";
    static dependencies = ["history", "userCommand"];
    static shared = ["getImageShapeGroups", "isTransformableShape", "isAnimableShape"];
    resources = {
        builder_actions: this.getActions(),
    };
    setup() {
        this.shapeDataCache = {};
        this.imageShapes = this.makeImageShapes();
    }
    getActions() {
        return {
            setImageShape: {
                load: async ({ editingElement, value: shapeName }) =>
                    this.loadShape(editingElement, { shape: shapeName }),
                apply: ({ editingElement: img, loadResult }) => {
                    img.dataset.shape = loadResult.shape;
                    img.dataset.shapeColors = loadResult.shapeColors;
                    img.src = loadResult.shapeDataURL;
                    const imgFilename = img.dataset.originalSrc.split("/").pop().split(".")[0];
                    img.dataset.fileName = `${imgFilename}.svg`;
                },
            },
            setImgShapeColor: {
                getValue: ({ editingElement: img, param: { index: colorIndex } }) =>
                    img.dataset.shapeColors?.split(";")[colorIndex] || "",
                load: async ({
                    editingElement: img,
                    param: { index: colorIndex },
                    value: color,
                }) => {
                    color = getValueFromVar(color);
                    const newColorId = parseInt(colorIndex);
                    const oldColors = img.dataset.shapeColors.split(";");
                    const newColors = oldColors.slice(0);
                    newColors[newColorId] = this.getCSSColorValue(
                        color === "" ? `o-color-${newColorId + 1}` : color
                    );
                    return this.loadShape(img, { shapeColors: newColors.join(";") });
                },
                apply: ({ editingElement: img, loadResult }) => {
                    img.dataset.shapeColors = loadResult.shapeColors;
                    img.src = loadResult.shapeDataURL;
                    img.classList.add("o_modified_image_to_save");
                },
            },
            flipImageShape: {
                load: async ({ editingElement: img, param: { axis } }) => {
                    const currentAxis = img.dataset.shapeFlip || "";
                    const newAxis = currentAxis.includes(axis)
                        ? currentAxis.replace(axis, "")
                        : currentAxis + axis;
                    return this.loadShape(img, { shapeFlip: newAxis === "yx" ? "xy" : newAxis });
                },
                apply: ({ editingElement: img, loadResult }) => {
                    if (loadResult.shapeFlip) {
                        img.dataset.shapeFlip = loadResult.shapeFlip;
                    } else {
                        delete img.dataset.shapeFlip;
                    }
                    img.src = loadResult.shapeDataURL;
                    img.classList.add("o_modified_image_to_save");
                },
            },
            rotateImageShape: {
                load: async ({ editingElement: img, param: { side } }) => {
                    const currentRotateValue = parseInt(img.dataset.shapeRotate) || 0;
                    const rotation = side === "left" ? -90 : 90;
                    const newRotateValue = (currentRotateValue + rotation + 360) % 360;
                    return this.loadShape(img, { shapeRotate: newRotateValue });
                },
                apply: ({ editingElement: img, loadResult }) => {
                    if (loadResult.shapeRotate) {
                        img.dataset.shapeRotate = loadResult.shapeRotate;
                    } else {
                        delete img.dataset.shapeRotate;
                    }
                    img.src = loadResult.shapeDataURL;
                    img.classList.add("o_modified_image_to_save");
                },
            },
            setImageShapeSpeed: {
                getValue: ({ editingElement: img }) => img.dataset.shapeAnimationSpeed || 0,
                load: async ({ editingElement: img, value: speed }) =>
                    this.loadShape(img, {
                        shapeAnimationSpeed: speed,
                    }),
                apply: ({ editingElement: img, loadResult }) => {
                    img.dataset.shapeAnimationSpeed = loadResult.shapeAnimationSpeed;
                    img.src = loadResult.shapeDataURL;
                    img.classList.add("o_modified_image_to_save");
                },
            },
        };
    }
    async getShapeData(shapeName) {
        let shape = this.shapeDataCache[shapeName];
        if (shape) {
            return shape;
        }
        const shapeURL = getShapeURL(shapeName);
        shape = await (await fetch(shapeURL)).text();
        this.shapeDataCache[shapeName] = shape;
        return shape;
    }
    async loadShape(img, newData = {}) {
        // todo: ensure that there is no problem having mutation on the image here.
        await this.loadImageInfos(img);
        const shapeName = newData.shape ?? img.dataset.shape;
        const shapeData = await this.getShapeData(shapeName);

        // Map the default palette colors to an array if the shape includes them
        // If they do not map a NULL, this way we know if a default color is in
        // the shape
        const oldColors = Object.values(DEFAULT_PALETTE).map((color) =>
            shapeData.includes(color) ? color : null
        );
        const shapeColors = newData.shapeColors ?? img.dataset.defaultShapeColors;
        const newColors = shapeColors?.split(";") || this.getDefaultNewColors(oldColors);
        const coloredShapeData = this.getColoredShapeData(shapeData, oldColors, newColors);

        const shapeDataURL = await this.computeShape(coloredShapeData, img, newData);
        //todo: handle hover effect before

        // todo: is it still needed?
        // await loadImage(shapeDataURL, img);
        return {
            ...newData,
            shapeColors: newColors.join(";"),
            shapeDataURL,
        };
        //todo: handle hover effect after
        // todo: find a way to apply to carousel thumbnail
    }
    async loadImageInfos(img) {
        await loadImageInfo(img);
    }

    /**
     * Sets the image in the supplied SVG and replace the src with a dataURL
     *
     * @param {string} svgText svg text file
     * @param {HTMLImageElement} img
     * @returns {Promise} resolved once the svg is properly loaded
     * in the document
     */
    async computeShape(svgText, img, newData = {}) {
        const getData = (propName) =>
            typeof newData[propName] !== "undefined" ? newData[propName] : img.dataset[propName];
        const params = {
            shape: getData("shape"),
            shapeAnimationSpeed: Number(getData("shapeAnimationSpeed")) || 0,
            shapeFlip: getData("shapeFlip") || "",
            shapeRotate: getData("shapeRotate") || 0,
            hoverEffect: getData("hoverEffect"),
            width: getData("resizeWidth") || getData("width") || img.naturalWidth,
        };

        // Apply the right animation speed if there is an animated shape.
        const shapeAnimationSpeed = params.shapeAnimationSpeed;
        if (shapeAnimationSpeed) {
            svgText = this.replaceAnimationDuration(shapeAnimationSpeed, svgText);
        }

        const svg = new DOMParser().parseFromString(svgText, "image/svg+xml").documentElement;

        // Modifies the SVG according to the "flip" or/and "rotate" options.
        const shapeFlip = params.shapeFlip;
        const shapeRotate = params.shapeRotate;
        if ((shapeFlip || shapeRotate) && this.isTransformableShape(params.shape)) {
            const shapeTransformValues = [];
            if (shapeFlip) {
                // Possible values => "x", "y", "xy"
                shapeTransformValues.push(
                    `scale${shapeFlip === "x" ? "X" : shapeFlip === "y" ? "Y" : ""}(-1)`
                );
            }
            if (shapeRotate) {
                // Possible values => "90", "180", "270"
                shapeTransformValues.push(`rotate(${shapeRotate}deg)`);
            }
            // "transform-origin: center;" does not work on "#filterPath". But
            // since its dimension is 1px * 1px the following solution works.
            const transformOrigin = "transform-origin: 0.5px 0.5px;";
            // Applies the transformation values to the path used to create a
            // mask over the SVG image.
            svg.querySelector("#filterPath").setAttribute(
                "style",
                `transform: ${shapeTransformValues.join(" ")}; ${transformOrigin}`
            );
        }

        // todo: Add shape animations on hover.
        // if (params.hoverEffect && this._canHaveHoverEffect()) {
        //     this._addImageShapeHoverEffect(svg, img);
        // }

        const svgAspectRatio =
            parseInt(svg.getAttribute("width")) / parseInt(svg.getAttribute("height"));
        // We will store the image in base64 inside the SVG.
        // applyModifications will return a dataURL with the current filters
        // and size options.
        const options = {
            mimetype: getImageMimetype(img),
            perspective: svg.dataset.imgPerspective || null,
            imgAspectRatio: svg.dataset.imgAspectRatio || null,
            svgAspectRatio: svgAspectRatio,
        };
        const imgDataURL = await applyModifications(img, options);
        svg.removeChild(svg.querySelector("#preview"));
        svg.querySelectorAll("image").forEach((image) => {
            image.setAttribute("xlink:href", imgDataURL);
        });
        // Force natural width & height (note: loading the original image is
        // needed for Safari where natural width & height of SVG does not return
        // the correct values).
        const originalImage = await loadImage(imgDataURL);
        // If the svg forces the size of the shape we still want to have the resized
        // width
        if (!svg.dataset.forcedSize) {
            svg.setAttribute("width", originalImage.naturalWidth);
            svg.setAttribute("height", originalImage.naturalHeight);
        } else {
            const imageWidth = Math.trunc(params.width);
            const newHeight = imageWidth / svgAspectRatio;
            svg.setAttribute("width", imageWidth);
            svg.setAttribute("height", newHeight);
        }
        // Transform the current SVG in a base64 file to be saved by the server
        const blob = new Blob([svg.outerHTML], {
            type: "image/svg+xml",
        });
        const dataURL = await createDataURL(blob);
        return dataURL;
    }
    /**
     * Replace animation durations in SVG and CSS with modified values.
     *
     * This function takes a ratio and an SVG string containing animations. It
     * uses regular expressions to find and replace the duration values in both
     * CSS animation rules and SVG duration attributes based on the provided
     * ratio.
     *
     * @param {number} speed The speed used to calculate the new animation
     *                       durations. If speed is 0.0, the original
     *                       durations are preserved.
     * @param {string} svg The SVG string containing animations.
     * @returns {string} The modified SVG string with updated animation
     *                   durations.
     */
    replaceAnimationDuration(speed, svg) {
        const ratio = (speed >= 0.0 ? 1.0 + speed : 1.0 / (1.0 - speed)).toFixed(3);
        // Callback for CSS 'animation' and 'animation-duration' declarations
        function callbackCssAnimationRule(match, declaration, value, unit, separator) {
            value = parseFloat(value) / (ratio ? ratio : 1);
            return `${declaration}${value}${unit}${separator}`;
        }

        // Callback function for handling the 'dur' SVG attribute timecount
        // value in accordance with the SMIL animation specification (e.g., 4s,
        // 2ms). If no unit is provided, seconds are implied.
        function callbackSvgDurTimecountVal(match, attribute_name, value, unit) {
            value = parseFloat(value) / (ratio ? ratio : 1);
            return `${attribute_name}${value}${unit ? unit : "s"}"`;
        }

        // Applying regex substitutions to modify animation speed in the 'svg'
        // variable.
        svg = svg.replace(CSS_ANIMATION_RULE_REGEX, callbackCssAnimationRule);
        svg = svg.replace(SVG_DUR_TIMECOUNT_VAL_REGEX, callbackSvgDurTimecountVal);
        if (CSS_ANIMATION_RATIO_REGEX.test(svg)) {
            // Replace the CSS --animation_ratio variable for future purpose.
            svg = svg.replace(CSS_ANIMATION_RATIO_REGEX, `--animation_ratio: ${ratio};`);
        } else {
            // Add the style tag with the root variable --animation ratio for
            // future purpose.
            const regex = /<svg .*>/m;
            const subst = `$&\n\t<style>\n\t\t:root { \n\t\t\t--animation_ratio: ${ratio};\n\t\t}\n\t</style>`;
            svg = svg.replace(regex, subst);
        }
        return svg;
    }

    getColoredShapeData(shapeData, oldColors, newColors) {
        for (const [i, color] of newColors.entries()) {
            shapeData = shapeData.replace(
                new RegExp(oldColors[i], "g"),
                this.getCSSColorValue(color)
            );
        }
        return shapeData;
    }
    getDefaultNewColors(oldColors) {
        return oldColors.map((color, i) =>
            color !== null ? this.getCSSColorValue(`o-color-${i + 1}`) : null
        );
    }
    applyShapeColors(editingElement, newColors) {}
    /**
     * Gets the CSS value of a color variable name so it can be used on shapes.
     *
     * @param {string} color
     * @returns {string}
     */
    getCSSColorValue(color) {
        if (!color || isCSSColor(color)) {
            return color;
        }
        return getCSSVariableValue(color);
    }
    isTransformableShape(shape) {
        if (!shape) {
            return false;
        }
        const canTransform = this.imageShapes[shape].transform;
        return typeof canTransform === "undefined" ? true : canTransform;
    }
    isAnimableShape(shape) {
        if (!shape) {
            return false;
        }
        return this.imageShapes[shape].animated;
    }
    getImageShapeGroups() {
        return imageShapeDefinitions;
    }
    makeImageShapes() {
        const entries = Object.values(this.getImageShapeGroups())
            .map((x) =>
                Object.values(x.subgroups)
                    .map((x) => Object.entries(x.shapes))
                    .flat()
            )
            .flat();
        return Object.fromEntries(entries);
    }
}
registry.category("website-plugins").add(ImageShapeOptionPlugin.id, ImageShapeOptionPlugin);
