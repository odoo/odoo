import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { convertCSSColorToRgba } from "@web/core/utils/colors";

/**
 * @typedef { Object } ImageHoverShared
 * @property { ImageHoverPlugin['setHoverEffect'] } setHoverEffect
 * @property { ImageHoverPlugin['removeHoverEffect'] } removeHoverEffect
 */

export class ImageHoverPlugin extends Plugin {
    static id = "imageHover";
    static shared = ["setHoverEffect", "removeHoverEffect"];
    static dependencies = ["imagePostProcess", "imageToolOption"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_actions: {
            SetHoverEffectAction,
            SetHoverEffectIntensityAction,
            SetHoverEffectColorAction,
            SetHoverEffectStrokeWidthAction,
        },
        system_attributes: ["data-original-src-before-hover"],
        default_shape_handlers: (dataset) =>
            dataset.hoverEffect && "html_builder/geometric/geo_square",
        post_compute_shape_listeners: async (svg, params) => {
            let rgba = null;
            let rbg = null;
            let opacity = null;
            // Add the required parts for the hover effects to the SVG.
            const hoverEffectName = params.hoverEffect;
            const hoverEffectsSvg = await this.getSvgHoverEffects();
            const hoverEffectEls = hoverEffectsSvg.querySelectorAll(`#${hoverEffectName} > *`);
            hoverEffectEls.forEach((hoverEffectEl) => {
                svg.appendChild(hoverEffectEl.cloneNode(true));
            });
            // Modifies the svg according to the chosen hover effect and the value
            // of the options.
            const animateEl = svg.querySelector("animate");
            const animateTransformEls = svg.querySelectorAll("animateTransform");
            const animateElValues = animateEl?.getAttribute("values");
            let animateTransformElValues = animateTransformEls[0]?.getAttribute("values");
            if (params.hoverEffectColor) {
                rgba = convertCSSColorToRgba(params.hoverEffectColor);
                rbg = `rgb(${rgba.red},${rgba.green},${rgba.blue})`;
                opacity = rgba.opacity / 100;
                if (!["outline", "image_mirror_blur"].includes(hoverEffectName)) {
                    svg.querySelector('[fill="hover_effect_color"]').setAttribute("fill", rbg);
                    animateEl.setAttribute(
                        "values",
                        animateElValues.replace("hover_effect_opacity", opacity)
                    );
                }
            }
            switch (hoverEffectName) {
                case "outline": {
                    svg.querySelector('[stroke="hover_effect_color"]').setAttribute("stroke", rbg);
                    svg.querySelector('[stroke-opacity="hover_effect_opacity"]').setAttribute(
                        "stroke-opacity",
                        opacity
                    );
                    // The stroke width needs to be multiplied by two because half
                    // of the stroke is invisible since it is centered on the path.
                    const strokeWidth = parseInt(params.hoverEffectStrokeWidth) * 2;
                    animateEl.setAttribute(
                        "values",
                        animateElValues.replace("hover_effect_stroke_width", strokeWidth)
                    );
                    break;
                }
                case "image_zoom_in":
                case "image_zoom_out":
                case "dolly_zoom": {
                    const imageEl = svg.querySelector("image");
                    const clipPathEl = svg.querySelector("#clip-path");
                    imageEl.setAttribute("id", "shapeImage");
                    // Modify the SVG so that the clip-path is not zoomed when the
                    // image is zoomed.
                    imageEl.setAttribute(
                        "style",
                        "transform-origin: center; width: 100%; height: 100%"
                    );
                    imageEl.setAttribute("preserveAspectRatio", "none");
                    svg.setAttribute("viewBox", "0 0 1 1");
                    svg.setAttribute("preserveAspectRatio", "none");
                    clipPathEl.setAttribute("clipPathUnits", "userSpaceOnUse");
                    const clipPathValue = imageEl.getAttribute("clip-path");
                    imageEl.removeAttribute("clip-path");
                    const gEl = document.createElementNS("http://www.w3.org/2000/svg", "g");
                    gEl.setAttribute("clip-path", clipPathValue);
                    imageEl.parentNode.replaceChild(gEl, imageEl);
                    gEl.appendChild(imageEl);
                    let zoomValue = 1.01 + parseInt(params.hoverEffectIntensity) / 200;
                    animateTransformEls[0].setAttribute(
                        "values",
                        animateTransformElValues.replace("hover_effect_zoom", zoomValue)
                    );
                    if (hoverEffectName === "image_zoom_out") {
                        // Set zoom intensity for the image.
                        const styleAttr = svg.querySelector("style");
                        styleAttr.textContent = styleAttr.textContent.replace(
                            "hover_effect_zoom",
                            zoomValue
                        );
                    }
                    if (hoverEffectName === "dolly_zoom") {
                        clipPathEl.setAttribute("style", "transform-origin: center;");
                        // Set zoom intensity for clip-path and overlay.
                        zoomValue = 0.99 - parseInt(params.hoverEffectIntensity) / 2000;
                        animateTransformEls.forEach((animateTransformEl, index) => {
                            if (index > 0) {
                                animateTransformElValues =
                                    animateTransformEl.getAttribute("values");
                                animateTransformEl.setAttribute(
                                    "values",
                                    animateTransformElValues.replace("hover_effect_zoom", zoomValue)
                                );
                            }
                        });
                    }
                    break;
                }
                case "image_mirror_blur": {
                    const imageEl = svg.querySelector("image");
                    imageEl.setAttribute("id", "shapeImage");
                    imageEl.setAttribute("style", "transform-origin: center;");
                    const imageMirrorEl = imageEl.cloneNode();
                    imageMirrorEl.setAttribute("id", "shapeImageMirror");
                    imageMirrorEl.setAttribute("filter", "url(#blurFilter)");
                    imageEl.insertAdjacentElement("beforebegin", imageMirrorEl);
                    const zoomValue = 0.99 - parseInt(params.hoverEffectIntensity) / 200;
                    animateTransformEls[0].setAttribute(
                        "values",
                        animateTransformElValues.replace("hover_effect_zoom", zoomValue)
                    );
                    break;
                }
            }
        },
        remove_hover_effect_handlers: this.removeHoverEffect.bind(this),
        set_hover_effect_handlers: this.setHoverEffect.bind(this),
    };

    defaultHoverEffectIntensity = 20;

    async setHoverEffect(imgEl, hoverEffectId = "overlay") {
        const updateAttributes = await this.dependencies.imagePostProcess.processImage({
            img: imgEl,
            newDataset: this.getDefaultValue(hoverEffectId),
        });
        updateAttributes();
    }

    async removeHoverEffect(imgEl) {
        const updateAttributes = await this.dependencies.imagePostProcess.processImage({
            img: imgEl,
            newDataset: {
                hoverEffect: undefined,
                hoverEffectColor: undefined,
                hoverEffectStrokeWidth: undefined,
                hoverEffectIntensity: undefined,
            },
        });
        updateAttributes();
    }
    /**
     * Gets the hover effects list.
     *
     * @private
     * @returns {Promise<SVGElement>}
     */
    async getSvgHoverEffects() {
        if (this.hoverEffectsSvg) {
            return this.hoverEffectsSvg;
        }
        const hoverEffectsURL = "/website/static/src/svg/hover_effects.svg";
        const text = await fetch(hoverEffectsURL).then((r) => r.text());
        const parser = new DOMParser();
        const xmlDoc = parser.parseFromString(text, "text/xml");
        this.hoverEffectsSvg = xmlDoc.getElementsByTagName("svg")[0];
        return this.hoverEffectsSvg;
    }
    getDefaultValue(hoverEffectId) {
        const defaultColor = { hoverEffectColor: "rgba(0, 0, 0, 0)" };
        const defaultEffectValues = {
            overlay: () => ({
                hoverEffectColor: this.dependencies.imageToolOption.getCSSColorValue("black-25"),
            }),
            outline: () => ({
                hoverEffectColor: this.dependencies.imageToolOption.getCSSColorValue("primary"),
                hoverEffectStrokeWidth: 10,
            }),
            image_zoom_in: () => defaultColor,
            image_zoom_out: () => defaultColor,
            dolly_zoom: () => defaultColor,
        };

        return {
            hoverEffectIntensity: String(this.defaultHoverEffectIntensity),
            ...defaultEffectValues[hoverEffectId]?.(),
            hoverEffect: hoverEffectId,
        };
    }
}
export class SetHoverEffectAction extends BuilderAction {
    static id = "setHoverEffect";
    static dependencies = ["imageHover"];

    isApplied({ editingElement, value: hoverEffectId }) {
        return editingElement.dataset.hoverEffect === hoverEffectId;
    }
    async apply({ editingElement, value: hoverEffectId, isPreviewing }) {
        await this.dependencies.imageHover.setHoverEffect(editingElement, hoverEffectId);
        if (isPreviewing) {
            // Wait a tick to ensure the interactions are restarted.
            // Simulate a mouseenter event to trigger the hover effect. (See
            // `ImageShapeHoverEffect`).
            setTimeout(() => {
                editingElement.dispatchEvent(new Event("mouseenter"));
            });
        }
    }
}
export class SetHoverEffectIntensityAction extends BuilderAction {
    static id = "setHoverEffectIntensity";
    static dependencies = ["imagePostProcess"];

    getValue({ editingElement }) {
        return parseInt(
            editingElement.dataset.hoverEffectIntensity || this.defaultHoverEffectIntensity,
            10
        );
    }
    async apply({ editingElement, value: intensity }) {
        const updateAttributes = await this.dependencies.imagePostProcess.processImage({
            img: editingElement,
            newDataset: {
                hoverEffectIntensity: String(intensity),
            },
        });
        updateAttributes();
    }
}
export class SetHoverEffectColorAction extends BuilderAction {
    static id = "setHoverEffectColor";
    static dependencies = ["imagePostProcess"];

    getValue({ editingElement }) {
        return editingElement.dataset.hoverEffectColor;
    }
    async apply({ editingElement, value: color }) {
        const updateAttributes = await this.dependencies.imagePostProcess.processImage({
            img: editingElement,
            newDataset: {
                hoverEffectColor: color,
            },
        });
        updateAttributes();
    }
}
export class SetHoverEffectStrokeWidthAction extends BuilderAction {
    static id = "setHoverEffectStrokeWidth";
    static dependencies = ["imagePostProcess"];

    getValue({ editingElement }) {
        return editingElement.dataset.hoverEffectStrokeWidth
            ? parseInt(editingElement.dataset.hoverEffectStrokeWidth, 10)
            : undefined;
    }
    async apply({ editingElement, value: strokeWidth }) {
        const updateAttributes = await this.dependencies.imagePostProcess.processImage({
            img: editingElement,
            newDataset: {
                hoverEffectStrokeWidth: String(strokeWidth),
            },
        });
        updateAttributes();
    }
}
registry.category("website-plugins").add(ImageHoverPlugin.id, ImageHoverPlugin);
