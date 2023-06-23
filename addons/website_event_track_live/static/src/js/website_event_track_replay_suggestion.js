/** @odoo-module **/

import { PublicWidget } from "@web/legacy/js/public/public_widget";

/**
 * The widget will have the responsibility to manage the interactions between the
 * Youtube player and the cover containing a replay button. This widget will
 * be used when no suggestion can be found in order to hide the Youtube suggestions.
 */
var WebsiteEventReplaySuggestion = PublicWidget.extend({
    template: 'website_event_track_live.website_event_track_replay_suggestion',
    events: {
        'click .owevent_track_suggestion_replay': '_onReplayClick'
    },

    init: function (parent, options) {
        this._super(...arguments);
        this.currentTrack = {
            'name': options.current_track.name,
            'imageSrc': options.current_track.website_image_url,
        };
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * If the user clicks on the replay button, the function will remove the
     * cover and send a new event to the parent to replay the video from the
     * beginning.
     */
    _onReplayClick: function () {
        this.trigger_up('replay');
        this.destroy();
    }
});

export default WebsiteEventReplaySuggestion;
