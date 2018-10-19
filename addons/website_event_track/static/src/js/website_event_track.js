odoo.define('website_event_track.website_event_track', function (require) {
"use strict";

var sAnimations = require('website.content.snippets.animation');

sAnimations.registry.websiteEventTrack = sAnimations.Class.extend({
    selector: '.o_website_event',
    read_events: {
        'keyup #event_track_search': '_onEventTrackSearch'
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Object} ev
     */
    _onEventTrackSearch: function (ev) {
        var change_text = $(ev.currentTarget).val();
        $('.event_track').removeClass('invisible');

        $("#search_summary").removeClass('invisible');
        if (change_text) {
            $("#search_number").text($(".event_track:containsLike("+change_text+")").length);
            $(".event_track:not(:containsLike("+change_text+"))").addClass('invisible');
        } else {
            $("#search_number").text(30);
        }

        ev.preventDefault();
    },

});

});
