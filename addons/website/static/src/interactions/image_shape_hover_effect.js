/** @odoo-module native */
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

const log = makeLogger("website.interaction.image_shape_hover_effect");

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
        this.sourceVersion = 0;
        this.sourceObserver = new MutationObserver(() => this.onSourceChanged());
        this.connectSourceObserver();
        this.adjustImageSourceFrom = this.bindDeferred(this.adjustImageSourceFrom);
        log.lifecycle("ImageShapeHoverEffect setup: src observer attached", () => ({
            hoverEffect: this.el.dataset.hoverEffect,
            hasSrc: !!this.originalImgSrc,
        }));
    }

    destroy() {
        log.lifecycle(
            "ImageShapeHoverEffect destroy: restore src, observer disconnected",
            () => ({
                hoverEffect: this.el.dataset.hoverEffect,
            }),
        );
        this.flushSourceChanges();
        this.cancelPendingHover?.();
        this.disconnectSourceObserver();
        if (this.originalImgSrc === null) {
            this.el.removeAttribute("src");
        } else {
            this.el.setAttribute("src", this.originalImgSrc);
        }
    }

    onSourceChanged() {
        this.originalImgSrc = this.el.getAttribute("src");
        this.sourceVersion++;
        this.svgInEl = null;
        this.svgOutEl = null;
        this.cancelPendingHover?.();
        log.logic(
            "ImageShapeHoverEffect source changed: invalidate animations",
            () => ({
                sourceVersion: this.sourceVersion,
            }),
        );
    }

    flushSourceChanges() {
        if (this.sourceObserver.takeRecords().length) {
            this.onSourceChanged();
        }
    }

    connectSourceObserver() {
        this.sourceObserver.observe(this.el, {
            attributes: true,
            attributeFilter: ["src"],
        });
    }
    disconnectSourceObserver() {
        if (this.sourceObserver) {
            this.sourceObserver.disconnect();
        }
    }

    mouseEnter() {
        this.lastMouseEvent = this.lastMouseEvent.then(async () => {
            this.flushSourceChanges();
            if (
                this.isDestroyed ||
                !this.originalImgSrc ||
                !this.el.dataset.hoverEffect
            ) {
                return;
            }
            const version = this.sourceVersion;
            const svg = this.svgInEl || (await this.loadSvg());
            this.flushSourceChanges();
            if (svg && !this.isDestroyed && version === this.sourceVersion) {
                await new Promise((resolve) => this.setImgSrc(svg, resolve));
            }
        });
    }

    async loadSvg() {
        const version = this.sourceVersion;
        const controller = new AbortController();
        let cancel;
        const cancelled = new Promise((resolve) => {
            cancel = () => {
                controller.abort();
                resolve(null);
            };
        });
        const forgetCleanup = this.registerCleanup(cancel);
        this.cancelPendingHover = cancel;
        const endFetch = log.perf("ImageShapeHoverEffect fetch svg");
        try {
            const response = fetch(this.originalImgSrc, {
                signal: controller.signal,
            }).then((response) => (response.ok ? response.text() : null));
            const text = await Promise.race([response, cancelled]);
            this.flushSourceChanges();
            if (!text || this.isDestroyed || version !== this.sourceVersion) {
                return null;
            }
            const document = new DOMParser().parseFromString(text, "text/xml");
            const svg = document.getElementsByTagName("svg")[0];
            if (!svg) {
                return null;
            }
            for (const animation of svg.querySelectorAll(
                "#hoverEffects animateTransform, #hoverEffects animate",
            )) {
                animation.removeAttribute("begin");
            }
            this.svgInEl = svg;
            return svg;
        } catch (error) {
            log.logic(
                "ImageShapeHoverEffect fetch failed, release hover queue",
                () => ({ error }),
            );
            return null;
        } finally {
            forgetCleanup();
            if (this.cancelPendingHover === cancel) {
                this.cancelPendingHover = null;
            }
            endFetch({ cancelled: controller.signal.aborted });
        }
    }

    getOutgoingSvg() {
        if (!this.svgOutEl) {
            this.svgOutEl = this.svgInEl.cloneNode(true);
            for (const animation of this.svgOutEl.querySelectorAll(
                "#hoverEffects animateTransform, #hoverEffects animate",
            )) {
                const values = animation.getAttribute("values");
                if (values !== null) {
                    animation.setAttribute(
                        "values",
                        values.split(";").reverse().join(";"),
                    );
                } else if (
                    animation.hasAttribute("from") &&
                    animation.hasAttribute("to")
                ) {
                    const from = animation.getAttribute("from");
                    animation.setAttribute("from", animation.getAttribute("to"));
                    animation.setAttribute("to", from);
                }
            }
        }
        return this.svgOutEl;
    }

    mouseLeave() {
        this.lastMouseEvent = this.lastMouseEvent.then(async () => {
            this.flushSourceChanges();
            if (
                this.isDestroyed ||
                !this.originalImgSrc ||
                !this.svgInEl ||
                !this.el.dataset.hoverEffect
            ) {
                return;
            }
            const version = this.sourceVersion;
            const svg = this.getOutgoingSvg();
            await new Promise((resolve) => this.setImgSrc(svg, resolve));
            if (!this.isDestroyed && version === this.sourceVersion) {
                // Editor mode restores the original after the reverse animation.
                await this.afterMouseLeave?.(svg, version);
            }
        });
    }

    /**
     * @param {HTMLElement} svg
     * @param {Function} resolve
     */
    setImgSrc(svg, resolve) {
        if (this.isDestroyed) {
            log.logic("ImageShapeHoverEffect setImgSrc: destroyed, drop");
            resolve();
            return;
        }
        const previousRandomClass = [...svg.classList].find((cl) =>
            cl.startsWith("o_shape_anim_random_"),
        );
        if (previousRandomClass) {
            svg.classList.remove(previousRandomClass);
        }
        svg.classList.add("o_shape_anim_random_" + Date.now());
        const svgString = new XMLSerializer().serializeToString(svg);
        this.setImageSource(
            `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svgString)}`,
            resolve,
        );
    }

    setImageSource(src, resolve) {
        if (this.isDestroyed) {
            resolve();
            return;
        }
        const version = this.sourceVersion;
        const preloadedImg = new Image();
        let settled = false;
        const finish = () => {
            if (settled) {
                return;
            }
            settled = true;
            if (this.cancelPendingHover === finish) {
                this.cancelPendingHover = null;
            }
            forgetCleanup();
            preloadedImg.removeEventListener("load", onPreload);
            preloadedImg.removeEventListener("error", onError);
            this.el.removeEventListener("load", finish);
            this.el.removeEventListener("error", onError);
            resolve();
        };
        const onError = () => {
            log.logic(
                "ImageShapeHoverEffect setImgSrc: image failed, release hover queue",
            );
            finish();
        };
        const onPreload = () => {
            preloadedImg.removeEventListener("load", onPreload);
            preloadedImg.removeEventListener("error", onError);
            this.flushSourceChanges();
            if (this.isDestroyed || version !== this.sourceVersion) {
                finish();
                return;
            }
            this.el.addEventListener("load", finish, { once: true });
            this.el.addEventListener("error", onError, { once: true });
            this.adjustImageSourceFrom(preloadedImg);
        };
        const forgetCleanup = this.registerCleanup(finish);
        this.cancelPendingHover = finish;
        preloadedImg.addEventListener("load", onPreload, { once: true });
        preloadedImg.addEventListener("error", onError, { once: true });
        preloadedImg.src = src;
    }

    /**
     * @param {HTMLImageElement} preloadedImageEl
     */
    adjustImageSourceFrom(preloadedImageEl) {
        if (this.isDestroyed) {
            return;
        }
        this.disconnectSourceObserver();
        this.el.src = preloadedImageEl.getAttribute("src");
        this.connectSourceObserver();
    }
}

registry
    .category("public.interactions")
    .add("website.image_shape_hover_effect", ImageShapeHoverEffect);
