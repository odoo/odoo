import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { pick } from "@web/core/utils/objects";
import { AssetsLoadingError, loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

/* global FB */
export class FacebookPage extends Interaction {
    static selector = ".o_facebook_page";
    dynamicContent = {
        _document: {
            "t-on-optionalCookiesAccepted": this.onOptionalCookiesAccepted,
        },
    };

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
        // Handle cookie warning fallback
        if (this.el.dataset.needCookiesApproval) {
            const fallbackEl = renderToElement("website.cookiesWarning");
            this.el.replaceChildren(fallbackEl);
        }
        this.renderFacebookPlugin(params);
        this.resizeObserver = new ResizeObserver(
            this.debounced(this.handleResize.bind(this, params), 100)
        );
        this.resizeObserver.observe(this.el);
        this.registerCleanup(() => { this.resizeObserver.disconnect() });
    }

    async willStart() {
       await this.loadFacebookSDK();
    }

    /**
     * Loads the Facebook SDK asynchronously by injecting the SDK script into the page.
     * If the script fails to load, it handles the error by checking the type of error
     * and whether the browser is online. In case of failure, it displays a warning
     * notification to the user about potential network issues or browser extensions
     * causing the problem.
     *
     * @async
     * @function
     * @throws {AssetsLoadingError} If the SDK script fails to load due to an asset loading issue.
     * @throws {Error} If there is a general error while loading the SDK script.
     */
    async loadFacebookSDK() {
        await loadJS("https://connect.facebook.net/en_US/sdk.js#xfbml=1&version=v10.0").catch(
            (error) => {
                if (!(error instanceof AssetsLoadingError || navigator.onLine)) {
                    const message = _t(
                        "Unable to load your Facebook page. This could be due to a network issue or browser extensions."
                    );
                    this.env.services.notification.add(message, { type: "warning" });
                }
            }
        );
    }

    /**
     * Handle resize events and render Facebook plugin if necessary.
     *
     * @param {Object} params
     */
    handleResize(params) {
        const currentWidth = this.el.offsetWidth;
        // Only re-render if width change is significant
        if (Math.abs(currentWidth - this.previousWidth) > 10) {
            this.previousWidth = currentWidth;
            this.renderFacebookPlugin(params);
        }
    }

    /**
     * Prepare Facebook plugin element & replace it with existing content.
     *
     * @param {Object} params
     */
    renderFacebookPlugin(params) {
        if (typeof FB !== "undefined") {
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
            // After accepting cookies there is not enough time to load the SDK
            setTimeout(() => {
                FB.XFBML.parse(this.el);
            }, 100); // 100ms delay
        }
    }
    /**
     * Load Facebook SDK and initialize the plugin.
     */
    async onOptionalCookiesAccepted() {
        // Remove the fallback element (cookie warning) if it exists
        const fallbackEl = this.el.querySelector(".o_no_optional_cookie");
        if (fallbackEl) {
            fallbackEl.remove();
        }
        await this.loadFacebookSDK();
        if (typeof FB !== "undefined") {
            FB.init({
                xfbml: true,
                version: "v10.0",
            });
            this.renderFacebookPlugin(this.el.dataset);
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
