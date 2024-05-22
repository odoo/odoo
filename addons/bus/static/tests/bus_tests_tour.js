odoo.define("bus.tour", function (require) {
    "use strict";

    const tour = require("web_tour.tour");

    tour.register("bundle_changed_notification", {
        test: true,
        url: '/web',
    }, [{
            trigger: '.o_web_client',
            run() {
                const webClient = odoo.__DEBUG__.services['web.web_client'];
                const _delayFn = webClient._getBundleNotificationDelay;
                webClient._getBundleNotificationDelay = () => 0;
                this.call('bus_service', 'trigger',
                    'notification',
                    [[['db_name', 'bundle_changed'], ['web.assets_backend', 'hash']]]
                );
                webClient._getBundleNotificationDelay = _delayFn;
            }
    }, {
            trigger: '.o_notification_title:contains(Refresh)',
        }]
    );
});
