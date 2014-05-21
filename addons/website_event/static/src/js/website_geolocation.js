(function() {
    "use strict";
    var website = openerp.website;

    website.snippet.animationRegistry.visitor = website.snippet.Animation.extend({
        selector: ".oe_country_events",
        start: function () {
            var self = this;
            $.post( "/event/get_country_event_list", function( data ) {
                if(data){
                    $( ".country_events_list" ).replaceWith( data );
                }
            });
        }
    });
})();