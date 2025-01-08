import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class ImageShapeHoverEffect extends Interaction {
    static selector = "img[data-hover-effect]";
    dynamicContent = {
        _root: {
            "t-on-mouseenter": this.mouseEnter,
            "t-on-mouseleave": this.mouseLeave,
        },
    };

    setup() {
        this.lastMouseEvent = Promise.resolve();
        this.originalImgSrc = this.el.getAttribute("src");
        this.svgInEl = null;
        this.svgOutEl = null;
    }

    destroy() {
        if (this.el.dataset.originalSrcBeforeHover && !this.el.classList.contains("o_modified_image_to_save")) {
            // Replace the image source by its original one if it has not been
            // modified in edit mode.
            this.el.src = this.el.dataset.originalSrcBeforeHover;
        } else if (this.originalImgSrc && (this.lastImgSrc === this.el.getAttribute("src"))) {
            this.el.src = this.originalImgSrc;
        }
        delete this.el.dataset.originalSrcBeforeHover;
    }

    mouseEnter() {
        if (!this.originalImgSrc || !this.el.dataset.hoverEffect) {
            return;
        }
        this.lastMouseEvent = this.lastMouseEvent.then(() => new Promise((resolve) => {
            if (!this.svgInEl) {
                fetch(this.el.src)
                    .then(response => response.text())
                    .then(text => {
                        const parser = new DOMParser();
                        const result = parser.parseFromString(text, "text/xml");
                        const svg = result.getElementsByTagName("svg")[0];
                        this.svgInEl = svg;
                        if (!this.svgInEl) {
                            resolve();
                            return;
                        }
                        // Start animations.
                        const animateEls = this.svgInEl.querySelectorAll("#hoverEffects animateTransform, #hoverEffects animate");
                        animateEls.forEach(animateTransformEl => {
                            animateTransformEl.removeAttribute("begin");
                        });
                        this.setImgSrc(this.svgInEl, resolve);
                    }).catch(() => {
                        // Could be the case if somehow the `src` is an absolute
                        // URL from another domain.
                    });
            } else {
                this.setImgSrc(this.svgInEl, resolve);
            }
        }));
    }

    mouseLeave() {
        this.lastMouseEvent = this.lastMouseEvent.then(() => new Promise((resolve) => {
            if (!this.originalImgSrc || !this.svgInEl || !this.el.dataset.hoverEffect) {
                resolve();
                return;
            }
            if (!this.svgOutEl) {
                // Reverse animations.
                this.svgOutEl = this.svgInEl.cloneNode(true);
                const animateTransformEls = this.svgOutEl.querySelectorAll("#hoverEffects animateTransform, #hoverEffects animate");
                animateTransformEls.forEach(animateTransformEl => {
                    let valuesValue = animateTransformEl.getAttribute("values");
                    valuesValue = valuesValue.split(";").reverse().join(";");
                    animateTransformEl.setAttribute("values", valuesValue);
                });
            }
            this.setImgSrc(this.svgOutEl, resolve);
        }));
    }

    /**
     * Converts the SVG to a data URI and set it as the image source.
     *
     * @param {HTMLElement} svg
￼    */
    setImgSrc(svg, resolve) {
        // Add random class to prevent browser from caching image. Otherwise the
        // animations do not trigger more than once.
        const previousRandomClass = [...svg.classList].find(cl => cl.startsWith("o_shape_anim_random_"));
        svg.classList.remove(previousRandomClass);
        svg.classList.add("o_shape_anim_random_" + Date.now());
        // Convert the SVG element to a data URI.
        const svg64 = btoa(new XMLSerializer().serializeToString(svg));
        // The image is preloaded to avoid a flickering when it is added to the
        // DOM.
        const preloadedImg = new Image();
        preloadedImg.src = `data:image/svg+xml;base64,${svg64}`;
        preloadedImg.onload = () => {
            if (this.isDestroyed) {
                // In some cases, it is possible for the "preloadedImg" to
                // finish loading while the widget has already been destroyed.
                // So, we do not set the image source because that can cause
                // unexpected reverse of the animation.
                resolve();
                return;
            }
            this.adjustImageSourceFrom(preloadedImg);
            this.lastImgSrc = preloadedImg.getAttribute("src");
            this.el.onload = () => {
                resolve();
            };
        };
    }

    /**
     * Overridable method called once the preloadedImageEl is loaded in
     * setImgSrc.
     *
     * @param {HTMLImageElement} preloadedImageEl
     */
    adjustImageSourceFrom(preloadedImageEl) {
        this.el.src = preloadedImageEl.getAttribute("src");
    }
}

registry
    .category("public.interactions")
    .add("website.image_shape_hover_effect", ImageShapeHoverEffect);
