odoo.define("website.tour.unsplash_beacon", function (require) {
"use strict";

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

const tour = require("web_tour.tour");

tour.register("test_unsplash_beacon", {
    test: true,
    url: "/?test_unsplash_beacon",
}, [{
    content: "Verify whether beacon was sent.",
    trigger: 'img[data-beacon="sent"]',
    run: () => {}, // This is a check.
}]);
});
