odoo.define("website.tour.unsplash_beacon", function (require) {
"use strict";

const tour = require("web_tour.tour");

tour.register("test_unsplash_beacon", {
    test: true,
    url: "/",
}, [{
    content: "Verify whether beacon was sent.",
    trigger: 'img[data-beacon="sent"]',
    run: () => {}, // This is a check.
}]);
});
