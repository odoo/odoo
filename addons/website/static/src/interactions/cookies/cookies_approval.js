import { registry } from "@web/core/registry";
import { MEDIAS_BREAKPOINTS, SIZES } from "@web/core/ui/ui_service";
import { renderToElement } from "@web/core/utils/render";
import { Interaction } from "@web/public/interaction";

export class CookiesApproval extends Interaction {
    static selector = "[data-need-cookies-approval]";

    setup() {
        this.iframeEl = this.el.tagName === "IFRAME" ? this.el : this.el.querySelector("iframe");
    }

    start() {
        if (this.iframeEl) {
            if (!this.cookiesWarningEl) {
                this.addOptionalCookiesWarning();
            }
        }
        this.addListener(
            document,
            "optionalCookiesAccepted",
            this.onOptionalCookiesAccepted,
            { once: true }
        );
    }

    get cookiesWarningEl() {
        if (this.iframeEl.nextElementSibling?.classList.contains("o_no_optional_cookie")) {
            return this.iframeEl.nextElementSibling;
        }
        return null;
    }

    addOptionalCookiesWarning() {
        const optionalCookiesWarningEl = renderToElement("website.cookiesWarning", {
            extraStyle: this.iframeEl.parentElement.classList.contains("media_iframe_video")
                ? `aspect-ratio: 16/9; max-width: ${MEDIAS_BREAKPOINTS[SIZES.SM].maxWidth}px;`
                : "",
            extraClasses: getComputedStyle(this.iframeEl.parentElement).position === "absolute"
                ? "" : "my-3",
        });
        this.insert(optionalCookiesWarningEl, this.iframeEl, "afterend");
        this.services["public.interactions"].startInteractions(optionalCookiesWarningEl);
    }

    onOptionalCookiesAccepted() {
        delete this.el.dataset.needCookiesApproval;
        if (this.iframeEl.dataset.nocookieSrc) {
            this.iframeEl.src = this.iframeEl.dataset.nocookieSrc;
            delete this.iframeEl.dataset.nocookieSrc;
        }
    }
}

registry.category("public.interactions").add("website.cookies_approval", CookiesApproval);
