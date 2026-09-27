import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { generateGMapLink } from "@website/js/utils";

/**
 * Bootstraps an "empty" Google Maps iframe.
 *
 * @returns {HTMLIframeElement}
 */
export function generateGMapIframe() {
    const iframeEl = document.createElement("iframe");
    iframeEl.classList.add("s_map_embedded", "o_not_editable");
    iframeEl.setAttribute("width", "100%");
    iframeEl.setAttribute("height", "100%");
    iframeEl.setAttribute("frameborder", "0");
    iframeEl.setAttribute("scrolling", "no");
    iframeEl.setAttribute("marginheight", "0");
    iframeEl.setAttribute("marginwidth", "0");
    iframeEl.setAttribute("src", "about:blank");
    iframeEl.setAttribute("aria-label", _t("Map"));
    return iframeEl;
}

export class Map extends Interaction {
    static selector = ".s_map";

    start() {
        if (!this.el.querySelector(".s_map_embedded")) {
            // The iframe is not found inside the snippet. This is probably due
            // to the sanitization of a field during the save, like in a product
            // description field. In such cases, reconstruct the iframe.
            const dataset = this.el.dataset;
            if (dataset.mapAddress) {
                const iframeEl = generateGMapIframe();
                this.el.querySelector(".s_map_color_filter").before(iframeEl);
                this.services.website_cookies.manageIframeSrc(iframeEl, generateGMapLink(dataset));
            }
        }
    }
}

registry.category("public.interactions").add("website.map", Map);
