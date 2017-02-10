odoo.define('website_event_track.website_event_track', function (require) {
"use strict";

$(document).ready(function() {

    $("#event_track_search").bind('keyup', function(){
        var change_text = $(this).val();
        $('.event_track').removeClass('invisible');

        $("#search_summary").removeClass('invisible');
        if (change_text) {
            var filtered_tracks = $(".event_track").filter(function() { return ( this.textContent || this.innerText || $(this).text() ).toUpperCase().indexOf( change_text.toUpperCase() ) <= -1; });
            $("#search_number").text(filtered_tracks.length);
            filtered_tracks.addClass('invisible');
        } else {
            $("#search_number").text(30);
        }

        event.preventDefault();
    });

});

});
