import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { DEFAULT_PALETTE } from "@html_editor/utils/color";
import { isCSSColor } from "@web/core/utils/colors";
import { getCSSVariableValue } from "@html_builder/utils/utils_css";
import { getShapeURL } from "./image_helpers";
import { activateCropper, createDataURL, loadImage } from "@html_editor/utils/image_processing";
import { getValueFromVar } from "@html_builder/utils/utils";
import { imageShapeDefinitions } from "./image_shapes_definition";
import {
    getImageTransformationData,
    shouldPreventGifTransformation,
} from "@html_editor/main/media/image_post_process_plugin";
import { _t } from "@web/core/l10n/translation";

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
    static dependencies = ["history", "userCommand", "imagePostProcess"];
    static shared = [
        "getImageShapeGroups",
        "isTransformableShape",
        "isAnimableShape",
        "isTogglableRatioShape",
        "getShapeLabel",
    ];
    resources = {
        builder_actions: this.getActions(),
        process_image_warmup_handlers: this.processImageWarmup.bind(this),
        process_image_post_handlers: this.processImagePost.bind(this),
    };
    setup() {
        this.shapeSvgTextCache = {};
        this.imageShapes = this.makeImageShapes();
    }
    getActions() {
        return {
            setImageShape: {
                load: async ({ editingElement: img, value: shapeId }) => {
                    const params = { shape: shapeId };
                    // todo nby: re-read the old option method `setImgShape` and be sure all the logic is in there
                    return this.loadShape(img, params);
                },
                apply: ({ editingElement: img, loadResult: updateImageAttributes }) => {
                    updateImageAttributes();
                    const imgFilename = img.dataset.originalSrc.split("/").pop().split(".")[0];
                    img.dataset.fileName = `${imgFilename}.svg`;
                },
            },
            setImgShapeColor: {
                getValue: ({ editingElement: img, params: { index: colorIndex } }) =>
                    img.dataset.shapeColors?.split(";")[colorIndex] || "",
                load: async ({
                    editingElement: img,
                    params: { index: colorIndex },
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
                apply: ({ loadResult: updateImageAttributes }) => {
                    updateImageAttributes();
                },
            },
            flipImageShape: {
                load: async ({ editingElement: img, params: { axis } }) => {
                    const currentAxis = img.dataset.shapeFlip || "";
                    const newAxis = currentAxis.includes(axis)
                        ? currentAxis.replace(axis, "")
                        : currentAxis + axis;
                    return this.loadShape(img, { shapeFlip: newAxis === "yx" ? "xy" : newAxis });
                },
                apply: ({ loadResult: updateImageAttributes }) => {
                    updateImageAttributes();
                },
            },
            rotateImageShape: {
                load: async ({ editingElement: img, params: { side } }) => {
                    const currentRotateValue = parseInt(img.dataset.shapeRotate) || 0;
                    const rotation = side === "left" ? -90 : 90;
                    const newRotateValue = (currentRotateValue + rotation + 360) % 360;
                    return this.loadShape(img, { shapeRotate: newRotateValue });
                },
                apply: ({ loadResult: updateImageAttributes }) => {
                    updateImageAttributes();
                },
            },
            setImageShapeSpeed: {
                getValue: ({ editingElement: img }) => img.dataset.shapeAnimationSpeed || 0,
                load: async ({ editingElement: img, value: speed }) =>
                    this.loadShape(img, {
                        shapeAnimationSpeed: speed,
                    }),
                apply: ({ loadResult: updateImageAttributes }) => {
                    updateImageAttributes();
                },
            },
            toggleImageShapeRatio: {
                isApplied: ({ editingElement: img }) => img.dataset.aspectRatio !== "1/1",
                load: async ({ editingElement: img }) => {
                    const isStretched = img.dataset.aspectRatio !== "1/1";
                    return this.loadShape(img, {
                        aspectRatio: isStretched ? "1/1" : "0/0",
                        x: undefined,
                        y: undefined,
                        width: undefined,
                        height: undefined,
                    });
                },
                apply: ({ editingElement: img, loadResult: updateImageAttributes }) => {
                    updateImageAttributes();
                },
            },
        };
    }
    async getShapeSvgText(shapeName) {
        let shapeSvgText = this.shapeSvgTextCache[shapeName];
        if (shapeSvgText) {
            return shapeSvgText;
        }
        const shapeURL = getShapeURL(shapeName);
        shapeSvgText = await (await fetch(shapeURL)).text();
        this.shapeSvgTextCache[shapeName] = shapeSvgText;
        return shapeSvgText;
    }
    async loadShape(img, newData = {}) {
        return this.dependencies.imagePostProcess.processImage({ img, newDataset: newData });
        //todo: handle hover effect before
        // todo: is it still needed?
        // await loadImage(shapeDataURL, img);
        // return {
        //     ...newData,
        //     shapeColors: newColors.join(";"),
        //     shapeDataURL,
        // };
        //todo: handle hover effect after
        // todo: find a way to apply to carousel thumbnail
    }
    async processImageWarmup(img, newDataset) {
        const getData = (propName) =>
            propName in newDataset ? newDataset[propName] : img.dataset[propName];
        const shapeId = getData("shape");
        // todo: should we reset some data if shapeName is not defined?
        if (!shapeId) {
            return;
        }
        const isNewShape = "shape" in newDataset && newDataset.shape !== img.dataset.shape;
        const shapeSvgText = await this.getShapeSvgText(shapeId);

        // Get colors.
        const defaultShapeColors = this.getThemedSvgColors(shapeSvgText).join(";");
        newDataset.shapeColors =
            newDataset.shapeColors ??
            (isNewShape ? defaultShapeColors : img.dataset.shapeColors ?? defaultShapeColors);

        const getNaturalWidth = async () => {
            if (img.naturalWidth) {
                return img.naturalWidth;
            }
            await new Promise((resolve, reject) => {
                img.addEventListener("load", () => resolve(img), { once: true });
                img.addEventListener("error", reject, { once: true });
            });
            return img.naturalWidth;
        };
        const svgWidth = getData("resizeWidth") || getData("width") || (await getNaturalWidth());

        // Get the svg element.
        const svg = this.computeShape(shapeSvgText, {
            shapeId,
            shapeFlip: getData("shapeFlip") || "",
            shapeRotate: getData("shapeRotate") || 0,
            shapeAnimationSpeed: Number(getData("shapeAnimationSpeed")) || 0,
            shapeColors: newDataset.shapeColors,
        });

        const svgAspectRatio =
            parseInt(svg.getAttribute("width")) / parseInt(svg.getAttribute("height"));
        const imgAspectRatio = svg.dataset.imgAspectRatio;

        if (isNewShape && !("aspectRatio" in newDataset)) {
            const data = getImageTransformationData({ ...img.dataset, ...newDataset });

            // The togglable ratio is squared by default.
            const shouldBeSquared =
                this.imageShapes[shapeId].togglableRatio && !img.dataset.aspectRatio;
            if (shouldBeSquared && !shouldPreventGifTransformation(data)) {
                newDataset.aspectRatio = "1/1";
            }
        }

        /**
         * @param {HTMLCanvasElement} canvas
         * @param {Object} data dataset containing the cropperDataFields
         */
        const postProcessCroppedCanvas = async (canvas) => {
            const img = await loadImage(canvas.toDataURL());
            document.createElement("div").appendChild(img);
            const cropper = await activateCropper(img, 1, { y: 0 });
            const croppedCanvas = cropper.getCroppedCanvas();
            cropper.destroy();
            return croppedCanvas;
        };

        return {
            getHeight: svg.dataset.imgPerspective && ((canvas) => canvas.width / svgAspectRatio),
            perspective: svg.dataset.imgPerspective || null,
            newDataset,
            // If imgAspectRatio is defined, the image is cropped a second time
            // after the first crop to ensure that the ratio of the shape and the
            // image are the same.
            postProcessCroppedCanvas: imgAspectRatio && postProcessCroppedCanvas,

            svg,
            svgAspectRatio,
            svgWidth,
        };
    }
    async processImagePost(b64url, handlerDataset, processContext) {
        const { svg, svgAspectRatio, svgWidth } = processContext;
        if (!svg) {
            return;
        }
        svg.querySelectorAll("image").forEach((image) => {
            image.setAttribute("xlink:href", b64url);
        });
        // Force natural width & height (note: loading the original image is
        // needed for Safari where natural width & height of SVG does not return
        // the correct values).
        const loadedImage = await loadImage(b64url);
        // If the svg forces the size of the shape we still want to have the resized
        // width
        if (!svg.dataset.forcedSize) {
            svg.setAttribute("width", loadedImage.naturalWidth);
            svg.setAttribute("height", loadedImage.naturalHeight);
        } else {
            const imageWidth = Math.trunc(svgWidth);
            const newHeight = imageWidth / svgAspectRatio;
            svg.setAttribute("width", imageWidth);
            svg.setAttribute("height", newHeight);
        }

        // Transform the current SVG in a base64 file to be saved by the server
        const blob = new Blob([svg.outerHTML], {
            type: "image/svg+xml",
        });
        const dataURL = await createDataURL(blob);
        return [dataURL, { ...handlerDataset, mimetype: "image/svg+xml" }];
    }

    /**
     * Sets the image in the supplied SVG and replace the src with a dataURL
     *
     * @param {string} svgText svg text file
     * @param {HTMLImageElement} img
     * @returns {SVGElement}
     */
    computeShape(svgText, { shapeId, shapeFlip, shapeRotate, shapeAnimationSpeed, shapeColors }) {
        // Apply the colors to the shape.
        svgText = this.replaceSvgColors(svgText, shapeColors.split(";"));
        // Apply the right animation speed if there is an animated shape.
        if (shapeAnimationSpeed) {
            svgText = this.replaceAnimationDuration(svgText, shapeAnimationSpeed);
        }

        const svg = new DOMParser().parseFromString(svgText, "image/svg+xml").documentElement;

        // Modifies the SVG according to the "flip" or/and "rotate" options.
        if ((shapeFlip || shapeRotate) && this.isTransformableShape(shapeId)) {
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

        svg.removeChild(svg.querySelector("#preview"));
        return svg;
    }
    /**
     * Replace animation durations in SVG and CSS with modified values.
     *
     * This function takes a ratio and an SVG string containing animations. It
     * uses regular expressions to find and replace the duration values in both
     * CSS animation rules and SVG duration attributes based on the provided
     * ratio.
     *
     * @param {string} svgText The SVG string containing animations.
     * @param {number} speed The speed used to calculate the new animation
     *                       durations. If speed is 0.0, the original
     *                       durations are preserved.
     * @returns {string} The modified SVG string with updated animation
     *                   durations.
     */
    replaceAnimationDuration(svgText, speed) {
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
        svgText = svgText.replace(CSS_ANIMATION_RULE_REGEX, callbackCssAnimationRule);
        svgText = svgText.replace(SVG_DUR_TIMECOUNT_VAL_REGEX, callbackSvgDurTimecountVal);
        if (CSS_ANIMATION_RATIO_REGEX.test(svgText)) {
            // Replace the CSS --animation_ratio variable for future purpose.
            svgText = svgText.replace(CSS_ANIMATION_RATIO_REGEX, `--animation_ratio: ${ratio};`);
        } else {
            // Add the style tag with the root variable --animation ratio for
            // future purpose.
            const regex = /<svg .*>/m;
            const subst = `$&\n\t<style>\n\t\t:root { \n\t\t\t--animation_ratio: ${ratio};\n\t\t}\n\t</style>`;
            svgText = svgText.replace(regex, subst);
        }
        return svgText;
    }

    replaceSvgColors(shapeSvgText, colors) {
        const svgColors = this.getSvgColors(shapeSvgText);
        for (const [i, color] of colors.entries()) {
            shapeSvgText = shapeSvgText.replace(
                new RegExp(svgColors[i], "g"),
                this.getCSSColorValue(color)
            );
        }
        return shapeSvgText;
    }
    getSvgColors(shapeSvgText) {
        // Map the default palette colors to an array if the shape includes them
        // If they do not map a NULL, this way we know if a default color is in
        // the shape
        return Object.values(DEFAULT_PALETTE).map((color) =>
            shapeSvgText.includes(color) ? color : null
        );
    }
    getThemedSvgColors(shapeSvgText) {
        const svgColors = this.getSvgColors(shapeSvgText);
        return svgColors.map((color, i) =>
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
    isTransformableShape(shapeId) {
        if (!shapeId) {
            return false;
        }
        const canTransform = this.imageShapes[shapeId].transform;
        return typeof canTransform === "undefined" ? true : canTransform;
    }
    getShapeLabel(shapeId) {
        if (!shapeId) {
            return _t("None");
        }
        return this.imageShapes[shapeId].selectLabel || _t("None");
    }
    isAnimableShape(shape) {
        if (!shape) {
            return false;
        }
        return this.imageShapes[shape].animated;
    }
    isTogglableRatioShape(shape) {
        if (!shape) {
            return false;
        }
        return this.imageShapes[shape].togglableRatio;
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
