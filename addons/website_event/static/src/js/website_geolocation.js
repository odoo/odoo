odoo.define('website_event.geolocation', ['website.snippets.animation'], function (require) {
"use strict";

var animation = require('website.snippets.animation');

animation.registry.visitor = animation.Animation.extend({
    selector: ".oe_country_events",
    start: function () {
        $.post( "/event/get_country_event_list", function( data ) {
            if(data){
                $( ".country_events_list" ).replaceWith( data );
            }
        });
    }
});

});
