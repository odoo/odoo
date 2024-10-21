/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_unsplash_beacon", {
    url: "/",
    steps: () => [{
        content: "Verify whether beacon was sent.",
        trigger: 'img[data-beacon="sent"]',
    }],
});
