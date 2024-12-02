import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { loadJS } from "@web/core/assets";

/* global FB */
export class FacebookPage extends Interaction {
    static selector = ".o_facebook_page";

    setup() {
        this.previousWidth = 0;
        const params = pick(
            this.el.dataset,
            "href",
            "id",
            "height",
            "width",
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

        this.renderFacebookPlugin(params);

        this.resizeObserver = new ResizeObserver(
            this.debounced(this.renderFacebookPlugin.bind(this, params), 100)
        );
        this.resizeObserver.observe(this.el);
        this.registerCleanup(() => { this.resizeObserver.disconnect() });
    }

    async willStart() {
        await loadJS("https://connect.facebook.net/en_US/sdk.js#xfbml=1&version=v10.0", {
            defer: "defer",
            crossorigin: "anonymous"
        });
    }

    /**
     * Prepare Facebook plugin element & replace it with existing content.
     *
     * @param {Object} params
    */
    renderFacebookPlugin(params) {
        if (typeof FB !== "undefined") {
            if (this.previousWidth !== params.width) {
                this.previousWidth = params.width;

                const fbDiv = document.createElement("div");
                fbDiv.className = "fb-page";
                fbDiv.setAttribute("data-href", params.href);
                fbDiv.setAttribute("data-tabs", params.tabs || "");
                fbDiv.setAttribute("data-width", params.width);
                fbDiv.setAttribute("data-height", params.height);
                fbDiv.setAttribute("data-small-header", params.small_header || "false");
                fbDiv.setAttribute("data-hide-cover", params.hide_cover || "false");

                this.el.replaceChildren(fbDiv);
                this.registerCleanup(() => {
                    fbDiv.remove();
                });
            }
            FB.XFBML.parse(this.el);
        }
    }
}

registry
    .category("public.interactions")
    .add("website.facebook_page", FacebookPage);

registry
    .category("public.interactions.edit")
    .add("website.facebook_page", {
        Interaction: FacebookPage,
    });
