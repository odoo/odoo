odoo.define("website.tour.website_edit_footer_only", function (require) {
"use strict";

const tour = require("web_tour.tour");

tour.register("test_edit_footer_only", {
    test: true,
    url: "/contactus",
}, [{
    content: "Enter edit mode",
    trigger: "a[data-action=edit]",
}, {
    content: "Drag separator into footer",
    trigger: "#oe_snippets .oe_snippet[name=Separator] .oe_snippet_thumbnail",
    run: "drag_and_drop footer div.col-lg-5:has(h5:contains(About)) p",
}, {
    content: "Save",
    trigger: "[data-action=save]",
    extra_trigger: "footer .s_hr",
}, {
    content: "Wait until saved",
    trigger: "[data-action=edit]",
}]);
});
