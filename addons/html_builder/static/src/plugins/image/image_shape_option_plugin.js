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

class ImageShapeOptionPlugin extends Plugin {
    static id = "imageShapeOption";
    static dependencies = ["history", "userCommand"];
    resources = {
        builder_actions: this.getActions(),
    };
    setup() {
        this.shapeDataCache = {};
    }
    getActions() {
        return {
            setImageShape: {
                load: async ({ editingElement, value: shapeName }) =>
                    this.loadShape(editingElement, shapeName),
                apply: ({ editingElement: img, value: shapeName, loadResult }) => {
                    img.dataset.shape = shapeName;

                    const imgFilename = img.dataset.originalSrc.split("/").pop().split(".")[0];
                    img.dataset.fileName = `${imgFilename}.svg`;

                    img.dataset.shapeColors = loadResult.shapeColors;
                    img.src = loadResult.shapeDataURL;
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
    async loadShape(img, shapeName, newColors) {
        // todo: ensure that there is no problem having mutation on the image here.
        await this.loadImageInfos(img);
        const shapeData = await this.getShapeData(shapeName);

        // Map the default palette colors to an array if the shape includes them
        // If they do not map a NULL, this way we know if a default color is in
        // the shape
        const oldColors = Object.values(DEFAULT_PALETTE).map((color) =>
            shapeData.includes(color) ? color : null
        );
        newColors = newColors || this.getDefaulteNewColors(oldColors);
        const coloredShapeData = this.getColoredShapeData(shapeData, oldColors, newColors);

        const shapeDataURL = await this.computeShape(coloredShapeData, img);
        //todo: handle hover effect before

        // todo: is it still needed?
        // await loadImage(shapeDataURL, img);
        return {
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
    async computeShape(svgText, img) {
        const params = {
            shapeAnimationSpeed: Number(img.dataset.shapeAnimationSpeed) || 0,
            shapeFlip: img.dataset.shapeFlip || "",
            shapeRotate: img.dataset.shapeRotate || 0,
            hoverEffect: img.dataset.hoverEffect,
            width: img.dataset.resizeWidth || img.dataset.width || img.naturalWidth,
        };

        // todo:
        // // Apply the right animation speed if there is an animated shape.
        // const shapeAnimationSpeed = params.shapeAnimationSpeed;
        // if (shapeAnimationSpeed) {
        //     svgText = this._replaceAnimationDuration(shapeAnimationSpeed, svgText);
        // }

        const svg = new DOMParser().parseFromString(svgText, "image/svg+xml").documentElement;

        // Modifies the SVG according to the "flip" or/and "rotate" options.
        const shapeFlip = params.shapeFlip;
        const shapeRotate = params.shapeRotate;
        if ((shapeFlip || shapeRotate) && this._isTransformableShape()) {
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

    getColoredShapeData(shapeData, oldColors, newColors) {
        for (const [i, color] of newColors.entries()) {
            shapeData = shapeData.replace(
                new RegExp(oldColors[i], "g"),
                this.getCSSColorValue(color)
            );
        }
        return shapeData;
    }
    getDefaulteNewColors(oldColors) {
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
}
registry.category("website-plugins").add(ImageShapeOptionPlugin.id, ImageShapeOptionPlugin);
