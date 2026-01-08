/** @odoo-module **/

import { PublicWidget } from "@web/legacy/js/public/public_widget";

var WebsiteEventTrackSuggestion = PublicWidget.extend({
    template: 'website_event_track_live.website_event_track_suggestion',
    events: {
        'click .owevent_track_suggestion_next': '_onNextTrackClick',
        'click .owevent_track_suggestion_close': '_onCloseClick',
        'click .owevent_track_suggestion_replay': '_onReplayClick'
    },

    init: function (parent, options) {
        this._super(...arguments);

        this.currentTrack = {
            'name': options.current_track.name,
            'imageSrc': options.current_track.website_image_url,
        };
        this.suggestion = {
            'name': options.suggestion.name,
            'speakerName': options.suggestion.speaker_name,
            'trackUrl': options.suggestion.website_url,
        };
    },

    start: function () {
        var self = this;
        this._super(...arguments).then(function () {
            self.timerInterval = setInterval(self._updateTimer.bind(self), 1000);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * If the user clicks on replay, remove this suggestion window and send an
     * event to the parent so that it can rewind the video to the beginning.
     */
    _onReplayClick: function () {
        this.trigger_up('replay');
        clearInterval(this.timerInterval);
        this.destroy();
    },

    _onCloseClick: function () {
        clearInterval(this.timerInterval);
        this.$('.owevent_track_suggestion_next').addClass('invisible');
    },

    _onNextTrackClick: function (ev) {
        if ($(ev.target).hasClass('owevent_track_suggestion_close')) {
            return;
        }

        window.location = this.suggestion.trackUrl;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _updateTimer: function () {
        var secondsLeft = parseInt(this.$('.owevent_track_suggestion_timer_text').text());

        if (secondsLeft > 1) {
            secondsLeft -= 1;
            this.$('.owevent_track_suggestion_timer_text').text(secondsLeft);
        } else {
            window.location = this.suggestion.trackUrl;
        }
    }
});

export default WebsiteEventTrackSuggestion;
