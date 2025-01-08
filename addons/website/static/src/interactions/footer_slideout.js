import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class FooterSlideout extends Interaction {
    static selector = "#wrapwrap";
    static selectorHas = ".o_footer_slideout";
    dynamicContent = {
        _root: {
            "t-att-class": () => ({
                "o_footer_effect_enable": this.slideoutEffect,
            }),
        },
    };

    setup() {
        this.slideoutEffect = this.el.querySelector(":scope > main").offsetHeight >= window.innerHeight;
    }

    start() {
        // On safari, add a pixel div over the footer, after in the DOM, and add
        // a background attachment on it as it fixes the glitches that appear
        // when scrolling the page with a footer slide out.
        // TODO check if the hack is still needed (might have been fixed when
        // the scrollbar was restored to its natural position).
        if (/^((?!chrome|android).)*safari/i.test(navigator.userAgent)) {
            const pixelEl = document.createElement("div");
            pixelEl.style.width = "1px";
            pixelEl.style.height = "1px";
            pixelEl.style.marginTop = "-1px";
            pixelEl.style.backgroundColor = "transparent";
            pixelEl.style.backgroundAttachment = "fixed";
            pixelEl.style.backgroundImage = "url(/website/static/src/img/website_logo.svg)";
            this.insert(pixelEl);
        }
    }
}

registry
    .category("public.interactions")
    .add("website.footer_slideout", FooterSlideout);

registry
    .category("public.interactions.edit")
    .add("website.footer_slideout", {
        Interaction: FooterSlideout,
    });
