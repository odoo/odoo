odoo.define("website.tour.contact", function (require) {
"use strict";

var core = require("web.core");
var tour = require("web_tour.tour");
var _t = core._t;

tour.register("contact", {
    url: "/page/contactus",
}, [{
    trigger: "li#customize-menu",
    content: _t("<b>Install a contact form</b> to improve this page."),
    extra_trigger: "#o_contact_mail",
    position: "bottom",
}, {
    trigger: "li#install_apps",
    content: _t("<b>Install new apps</b> to get more features. Let's install the <i>'Contact form'</i> app."),
    position: "bottom",
}]);
});
