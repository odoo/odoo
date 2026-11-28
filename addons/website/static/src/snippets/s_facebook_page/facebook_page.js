import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { clamp } from "@web/core/utils/numbers";
import { pick } from "@web/core/utils/objects";
import { getFacebookPageId } from "@website/js/utils";

/**
 * Returns the default accessible name of the Facebook page.
 *
 * @param {HTMLElement} el
 * @returns {string}
 */
function getDefaultName(el) {
    const page = el.dataset.id || getFacebookPageId(el.dataset.href || "");
    return page ? _t("Facebook page: %(page)s", { page }) : _t("Facebook page");
}

export class FacebookPage extends Interaction {
    static selector = ".o_facebook_page";

    setup() {
        this.previousWidth = 0;
        const params = pick(
            this.el.dataset,
            "href",
            "id",
            "height",
            "tabs",
            "small_header",
            "hide_cover"
        );
        if (!params.href) {
            return;
        }
        if (params.id) {
            params.href = `https://www.facebook.com/${params.id}`;
            delete params.id;
        }

        this.renderIframe(params);

        this.resizeObserver = new ResizeObserver(
            this.debounced(this.renderIframe.bind(this, params), 100)
        );
        this.resizeObserver.observe(this.el.parentElement);
        this.registerCleanup(() => {
            this.resizeObserver.disconnect();
        });
    }

    /**
     * Prepare iframe element & replace it with existing iframe.
     *
     * @param {Object} params
     */
    renderIframe(params) {
        params.width = clamp(Math.floor(this.el.getBoundingClientRect().width), 180, 500);
        if (this.previousWidth !== params.width) {
            this.previousWidth = params.width;
            const searchParams = new URLSearchParams(params);

            const iframeEl = document.createElement("iframe");
            iframeEl.setAttribute("style", "border: none; overflow: hidden;");
            iframeEl.title = this.el.dataset.accessibleName || getDefaultName(this.el);
            iframeEl.height = params.height;
            iframeEl.width = params.width;

            this.el.replaceChildren(iframeEl);
            this.registerCleanup(() => {
                iframeEl.remove();
            });

            const src = "https://www.facebook.com/plugins/page.php?" + searchParams;
            this.services.website_cookies.manageIframeSrc(iframeEl, src);
        }
    }
}

registry.category("public.interactions").add("website.facebook_page", FacebookPage);
registry.category("website.accessible_names").add("website.facebook_page", {
    selector: FacebookPage.selector,
    getDefaultName,
});
