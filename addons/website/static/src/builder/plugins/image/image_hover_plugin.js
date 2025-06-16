import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { convertCSSColorToRgba } from "@web/core/utils/colors";

export class ImageHoverPlugin extends Plugin {
    static id = "imageHover";
    resources = {
        builder_actions: {
            setHoverEffect: {
                load: async () => {},
                apply: async (params) => {},
            },
        },
        post_compute_shape_listeners: async (svg, params) => {
            let rgba = null;
            let rbg = null;
            let opacity = null;
            // Add the required parts for the hover effects to the SVG.
            const hoverEffectName = params.hoverEffect;
            await this.getHoverEffects();
            const hoverEffectEls = this.hoverEffectsSvg.querySelectorAll(`#${hoverEffectName} > *`);
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
    };
    /**
     * Gets the hover effects list.
     *
     * @private
     * @returns {Promise<SVGElement>}
     */
    async getHoverEffects() {
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
}
registry.category("website-plugins").add(ImageHoverPlugin.id, ImageHoverPlugin);
