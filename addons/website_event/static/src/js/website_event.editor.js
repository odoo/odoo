odoo.define('website_event.editor', function (require) {
"use strict";

var core = require('web.core');
var contentMenu = require('website.contentMenu');
var website = require('website.website');

var _t = core._t;

contentMenu.TopBar.include({
    new_event: function() {
        website.prompt({
            id: "editor_new_event",
            window_title: _t("New Event"),
            input: "Event Name",
        }).then(function (event_name) {
            website.form('/event/add_event', 'POST', {
                event_name: event_name
            });
        });
    },
});

});
