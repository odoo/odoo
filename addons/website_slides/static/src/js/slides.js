odoo.define('website_slides.slides', function (require) {
'use strict';

var time = require('web.time');
var sAnimations = require('website.content.snippets.animation');

sAnimations.registry.websiteSlides = sAnimations.Class.extend({
    selector: '#wrapwrap',
    read_events: {
        'click .o_slides_hide_channel_settings': '_onHideChannelSettings',
    },

    /**
     * @override
     * @param {Object} parent
     */
    start: function (parent) {
        var defs = [this._super.apply(this, arguments)];

        _.each($("timeago.timeago"), function (el) {
            var datetime = $(el).attr('datetime');
            var datetimeObj = time.str_to_datetime(datetime);
            // if presentation 7 days, 24 hours, 60 min, 60 second, 1000 millis old(one week)
            // then return fix formate string else timeago
            var displayStr = '';
            if (datetimeObj && new Date().getTime() - datetimeObj.getTime() > 7 * 24 * 60 * 60 * 1000) {
                displayStr = moment(datetimeObj).format('ll');
            } else {
                displayStr = moment(datetimeObj).fromNow();
            }
            $(el).text(displayStr);
        });

        return $.when.apply($, defs);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * To prevent showing channel settings alert box once user closed it.
     *
     * @private
     * @param {Object} ev
     */
    _onHideChannelSettings: function (ev) {
        ev.preventDefault();
        var channelID = $(ev.currentTarget).data('channelId');
        document.cookie = 'slides_channel_' + channelID + ' = closed';
    },
});
});
