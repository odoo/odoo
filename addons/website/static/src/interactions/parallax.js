import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

class Parallax extends Interaction {
    static selector = ".parallax";
    dynamicSelectors = Object.assign(this.dynamicSelectors, {
        _modal: () => this.modalEl
    });
    dynamicContent = {
        _document: {
            "t-on-scroll": this.onScroll,
        },
        _window: {
            "t-on-resize": this.onResize,
        },
        _modal: {
            "t-on-shown.bs.modal": this.onModalShown,
        }
    }

    setup() {
        this.speed = 0;
        this.ratio = 0;
        this.viewportHeight = 0;
        this.parallaxHeight = 0;
        this.minScrollPos = 0;
        this.maxScrollPos = 0;

        this.modalEl = this.el.closest(".modal");
        this.bgEl = this.el.querySelector(":scope > .s_parallax_bg");
    }

    start() {
        this.rebuild();
    }

    destroy() {
        this.updateBgCSS({ top: "", bottom: "", transform: "" });
    }

    onModalShown() {
        this.rebuild();
        this.modalEl.dispatchEvent(new Event("scroll"));
    }

    updateBgCSS(options) {
        // this.options.wysiwyg?.odooEditor.observerUnactive('updateBgCSS');
        Object.assign(this.bgEl.style, options);
        // this.options.wysiwyg?.odooEditor.observerActive('updateBgCSS');
    }

    rebuild() {
        this.speed = parseFloat(this.el.getAttribute("data-scroll-background-ratio")) || 0;
        if (this.speed === 0 || this.speed === 1) {
            return;
        }
        this.viewportHeight = document.body.clientHeight;
        this.parallaxHeight = this.el.getBoundingClientRect().height;

        // The parallax is in the viewport if it is between these two values 
        // min : bottom of the parallax in at the top of the page
        // max : top of the parallax in at the bottom of the page
        this.minScrollPos = - this.parallaxHeight;
        this.maxScrollPos = this.viewportHeight;

        this.ratio = this.speed * (this.viewportHeight / 10);

        this.updateBgCSS({ top: -Math.abs(this.ratio) + "px", bottom: -Math.abs(this.ratio) + "px" })
    }

    onResize() {
        this.rebuild();
    }

    onScroll() {
        const currentPosition = this.el.getBoundingClientRect().top;
        if (this.speed === 0
            || this.speed === 1
            || currentPosition < this.minScrollPos
            || currentPosition > this.maxScrollPos) {
            return;
        }

        const r = 1 / (this.minScrollPos - this.maxScrollPos);
        const offset = 1 - 2 * this.minScrollPos * r;
        const movement = - Math.round(this.ratio * (r * currentPosition + offset));

        this.updateBgCSS({ transform: "translateY(" + movement + "px)" });
    }
}

registry
    .category("public.interactions")
    .add("website.parallax", Parallax);
