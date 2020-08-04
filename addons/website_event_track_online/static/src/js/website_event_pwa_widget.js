odoo.define("website_event_track_online.website_event_pwa_widget", function (require) {
    "use strict";

    var config = require("web.config");
    var publicWidget = require("web.public.widget");

    var PWAInstallBanner = publicWidget.Widget.extend({
        xmlDependencies: ["/website_event_track_online/static/src/xml/website_event_pwa.xml"],
        template: "pwa_install_banner",
        events: {
            "click .o_btn_install": "_onClickInstall",
        },

        /**
         * @private
         */
        _onClickInstall: function () {
            this.trigger_up("prompt_install");
        },
    });

    publicWidget.registry.WebsiteEventPWAWidget = publicWidget.Widget.extend({
        selector: "#wrapwrap.event",
        custom_events: {
            prompt_install: "_onPromptInstall",
        },

        /**
         *
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.beforeInstallPromptHandler = this._onBeforeInstallPrompt.bind(this);
        },

        /**
         *
         * @override
         */
        start: function () {
            var superProm = this._super.apply(this, arguments);
            window.addEventListener("beforeinstallprompt", this.beforeInstallPromptHandler);
            return superProm.then(this._registerServiceWorker);
        },

        /**
         *
         * @override
         */
        destroy: function () {
            window.removeEventListener("beforeinstallprompt", this.beforeInstallPromptHandler);
            this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * @private
         */
        _hideInstallBanner: function () {
            this.installBanner ? this.installBanner.destroy() : undefined;
        },

        /**
         *
         * @private
         */
        _registerServiceWorker: function () {
            if (!("serviceWorker" in navigator)) {
                return;
            }
            navigator.serviceWorker
                .register("/event/service-worker.js", { scope: "/event" })
                .then((registration) => {
                    console.info("Registration successful, scope is:", registration.scope);
                })
                .catch((error) => {
                    console.error("Service worker registration failed, error:", error);
                });
        },

        /**
         * @private
         */
        _showInstallBanner: function () {
            this.installBanner = new PWAInstallBanner(this);
            this.installBanner.appendTo(this.$el);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param ev {Event}
         */
        _onBeforeInstallPrompt: function (ev) {
            if (!config.device.isMobile) {
                return;
            }
            ev.preventDefault();
            this.deferredPrompt = ev;
            this._showInstallBanner();
        },

        /**
         * @private
         * @param ev {Event}
         */
        _onPromptInstall: function (ev) {
            ev.stopPropagation();
            this.deferredPrompt.prompt();
            this._hideInstallBanner();
            this.deferredPrompt.userChoice.then((choiceResult) => {
                if (choiceResult.outcome === "accepted") {
                    console.log("User accepted the install prompt");
                } else {
                    console.log("User dismissed the install prompt");
                }
            });
        },
    });

    return {
        PWAInstallBanner: PWAInstallBanner,
        WebsiteEventPWAWidget: publicWidget.registry.WebsiteEventPWAWidget,
    };
});
