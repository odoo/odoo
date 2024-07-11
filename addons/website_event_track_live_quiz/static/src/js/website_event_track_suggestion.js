/** @odoo-module **/

import WebsiteEventTrackSuggestion from "@website_event_track_live/js/website_event_track_suggestion";

var WebsiteEventTrackSuggestionLiveQuiz = WebsiteEventTrackSuggestion.include({
    events: Object.assign({}, WebsiteEventTrackSuggestion.prototype.events, {
        'click .owevent_track_suggestion_quiz': '_onQuizClick'
    }),

    init: function (parent, options) {
        this._super(...arguments);
        this.currentTrack.showQuiz = options.current_track.show_quiz;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * If the user takes the quiz, stop the next suggestion timer
     */
    _onQuizClick: function () {
        clearInterval(this.timerInterval);
        this.$('.owevent_track_suggestion_timer_text_wrapper').remove();
    }
});

export default WebsiteEventTrackSuggestionLiveQuiz;
