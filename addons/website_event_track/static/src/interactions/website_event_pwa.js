import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { utils as uiUtils } from "@web/core/ui/ui_service";

export class WebsiteEventPWA extends Interaction {
    static selector = "#wrapwrap.event";

    dynamicContent = {
        _window : { "t-on-beforeinstallprompt.prevent": (event) => this.showInstallBanner(event) },
        ".o_btn_close": { "t-on-click": this.hideInstallBanner },
        ".o_btn_install": { "t-on-click": this.onPromptInstall },
    };

    async willStart() {
        await this.registerServiceWorker().then(this.prefetch());
    }

    /**
     * Returns the PWA's scope
     *
     * Note: this method performs a matching to handle URLs with the language prefix.
     *       Typically this prefix is in the form of "en" or "en_US" but it can also be
     *       any string using the customization options in the Website's settings.
     * @returns {String}
     */
    getScope() {
        var matches = window.location.pathname.match(/^(\/(?:event|[^/]+\/event))\/?/);
        if (matches && matches[1]) {
            return matches[1];
        }
        return "/event";
    }

    hideInstallBanner() {
        this.installBanner ? this.installBanner[0].remove() : undefined;
        const shadowHostEl = document.querySelector(".o-livechat-root");
        const livechatButtonEl = shadowHostEl?.shadowRoot.querySelector(".o-livechat-LivechatButton");
        if (livechatButtonEl) {
            livechatButtonEl.style.position = "";
            livechatButtonEl.style.bottom = "0";
        }
    }

    /**
     * Parse the current page for first-level children pages and ask the ServiceWorker
     * to already fetch them to populate the cache.
     */
    prefetch() {
        if (!("serviceWorker" in navigator)) {
            return;
        }
        var assetsUrls = Array.from(document.querySelectorAll("link[rel='stylesheet'], script[src]")).map(function (el) {
            return el.href || el.src;
        });
        navigator.serviceWorker.ready.then(function (registration) {
            registration.active.postMessage({
                action: "prefetch-assets",
                urls: assetsUrls,
            });
        }).catch(function (error) {
            console.error("Service worker ready failed, error:", error);
        });
        var currentPageUrl = window.location.href;
        var childrenPagesUrls = Array.from(document.querySelectorAll("a[href^='" + this.getScope() + "/']")).map(function (el) {
            return el.href;
        });
        navigator.serviceWorker.ready.then(function (registration) {
            registration.active.postMessage({
                action: "prefetch-pages",
                urls: childrenPagesUrls.concat(currentPageUrl),
            });
        }).catch(function (error) {
            console.error("Service worker ready failed, error:", error);
        });
    }

    async registerServiceWorker() {
        if (!("serviceWorker" in navigator)) {
            return;
        }
        var scope = this.getScope();
        return navigator.serviceWorker
            .register(scope + "/service-worker.js", { scope: scope })
            .catch(function (error) {
                console.error("Service worker registration failed, error:", error);
            });
    }

    showInstallBanner(ev) {
        if (!uiUtils.isSmall()) {
            return;
        }
        this.beforeInstallEvent = ev;
        this.installBanner = this.renderAt("website_event_track.pwa_install_banner");
        
        // If Livechat available, It should be placed above the PWA banner.
        const height = document.querySelector(".o_pwa_install_banner").offsetHeight;
        const shadowHostEl = document.querySelector(".o-livechat-root");
        const livechatButtonEl = shadowHostEl?.shadowRoot.querySelector(".o-livechat-LivechatButton");
        if (livechatButtonEl) {
            livechatButtonEl.style.position = "relative";
            livechatButtonEl.style.bottom = `${height}px`;
        }
    }

    onPromptInstall() {
        this.hideInstallBanner();
        this.beforeInstallEvent.prompt();
        this.beforeInstallEvent.userChoice.then((choiceResult) => {
            if (choiceResult.outcome === "accepted") {
                console.log("User accepted the install prompt");
            } else {
                console.log("User dismissed the install prompt");
            }
        });
    }
}

registry
    .category("public.interactions")
    .add("website_event_track.website_event_pwa", WebsiteEventPWA);
