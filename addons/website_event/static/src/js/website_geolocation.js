odoo.define('website_event.geolocation', function (require) {
"use strict";

var animation = require('web_editor.snippets.animation');

animation.registry.visitor = animation.Class.extend({
    selector: ".oe_country_events, .country_events",
    start: function () {
        var self = this;
        $.get("/event/get_country_event_list").then(function( data ) {
            if(data){
                self.$(".country_events_list").replaceWith( data );
            }
        });
    }
});

});
