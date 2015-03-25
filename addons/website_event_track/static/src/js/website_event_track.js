odoo.define('website_event_track.website_event_track', function (require) {
"use strict";

$(document).ready(function() {

    $("#event_track_search").bind('keyup', function(){
        var change_text = $(this).val();
        $('.event_track').removeClass('invisible');

        $("#search_summary").removeClass('invisible');
        if (change_text) {
            $("#search_number").text($(".event_track:Contains("+change_text+")").length);
            $(".event_track:not(:Contains("+change_text+"))").addClass('invisible');
        } else {
            $("#search_number").text(30);
        }

        event.preventDefault();
    });

});

});
