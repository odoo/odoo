odoo.define('website_event_track.website_event_track', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');
var _t = core._t;

publicWidget.registry.websiteEventTrack = publicWidget.Widget.extend({
    selector: '.o_wevent_event',
    events: {
        'input #event_track_search': '_onEventTrackSearchInput',
        'click .o_wevent_track_tag': '_onEventTagClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onEventTrackSearchInput: function (ev) {
        ev.preventDefault();

        var text = $(ev.currentTarget).val();
        var filter = _.str.sprintf(':containsLike(%s)', text);

        this.$('#search_summary').removeClass('invisible');
        var $tracks = $('.event_track');
        this.$('#search_count').text(_.str.sprintf(_t('%s found'), $tracks.filter(filter).length));
        $tracks.removeClass('o_wevent_track_invisible').not(filter).addClass('o_wevent_track_invisible');
    },

    /**
     *
     * Allows to easily search tracks while staying on the agenda page.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onEventTagClick: function (ev) {
        this.$('#event_track_search').val(
            $(ev.currentTarget).find('span').text()
        ).trigger('input');
    },
});

return publicWidget.registry.websiteEventTrack;

});
