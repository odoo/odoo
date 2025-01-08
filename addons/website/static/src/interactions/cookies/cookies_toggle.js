import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { onceAllImagesLoaded } from "@website/utils/images";

export class CookiesToggle extends Interaction {
    static selector = ".o_cookies_bar_toggle";

    dynamicContent = {
        "_root": { "t-on-click": this.onClick },
        ".fa:t-att-class": () => ({
                "fa-eye": !this.modalShown,
                "fa-eye-slash": this.modalShown,
        }),
        ".o_cookies_bar_toggle_label:t-out": this.toggleText,
    };

    setup() {
        this.cookiesModalEl = this.el.nextElementSibling.querySelector(".modal");
    }

    start() {
        this.addListener(this.services.website_cookies.bus, "cookiesBar.discard", this.onClick);
    }

    get modalShown() {
        return this.cookiesModalEl.classList.contains("show");
    }

    toggleText() {
        return this.modalShown ? _t("Hide the cookies bar") : _t("Show the cookies bar");
    }

    async onClick(ev) {
        if (ev.currentTarget === this.el) {
            this.services.website_cookies.bus.trigger("cookiesBar.toggle");
        }

        // Changing the property cannot be done in "t-att-style" in
        // dynamicContent as it relies on async code.
        if (!this.modalShown || !this.cookiesModalEl.classList.contains("s_popup_bottom")) {
            this.el.style.removeProperty("--cookies-bar-toggle-inset-block-end");
        } else {
            // Lazy-loaded images don't have a height yet. We need to await them
            await this.waitFor(onceAllImagesLoaded(this.cookiesModalEl));
            const popupHeight = this.cookiesModalEl.querySelector(".modal-content").offsetHeight;
            const toggleMargin = 8;
            // Avoid having the toggle over another button, but if the cookies
            // bar is too tall, place it at the bottom anyway.
            const bottom = document.body.offsetHeight > popupHeight + this.el.offsetHeight + toggleMargin
                ? `calc(
                    ${getComputedStyle(this.cookiesModalEl.querySelector(".modal-dialog")).paddingBottom}
                    + ${popupHeight + toggleMargin}px
                )`
                : "";
            this.el.style.setProperty("--cookies-bar-toggle-inset-block-end", bottom);
        }
    }
}

registry.category("public.interactions").add("website.cookies_toggle", CookiesToggle);
