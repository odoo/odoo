/** @odoo-module **/

import { registry } from "@web/core/registry";

if (window.location.search.includes("test_unsplash_beacon")) {
    // Patch RPC call.
    const oldGet = $.get.bind($);
    $.get = (url, data, success, dataType) => {
        if (url === "https://views.unsplash.com/v") {
            const imageEl = document.querySelector(`img[src^="/unsplash/${data.photo_id}/"]`);
            imageEl.dataset.beacon = "sent";
            return;
        }
        return oldGet(url, data, success, dataType);
    };
}

registry.category("web_tour.tours").add("test_unsplash_beacon", {
    test: true,
    url: "/?test_unsplash_beacon",
    steps: [{
        content: "Verify whether beacon was sent.",
        trigger: 'img[data-beacon="sent"]',
        isCheck: true,
    }],
});
