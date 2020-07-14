odoo.define("website_event_track_online.website_event_pwa_widget", function (require) {
    "use strict";

    var publicWidget = require("web.public.widget");

    publicWidget.registry.WebsiteEventPWAWidget = publicWidget.Widget.extend({
        selector: "#wrapwrap.event",

        start: function () {
            var superPromise = this._super.apply(this, arguments);
            this._registerServiceWorker();
            return superPromise;
        },

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
    });

    return publicWidget.registry.WebsiteEventPWAWidget;
});
