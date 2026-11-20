/** @odoo-module **/

import Quiz from "@website_event_track_quiz/js/event_quiz";

var WebsiteEventTrackSuggestionQuiz = Quiz.include({
    /**
     * @override
     */
    willStart: function () {
        return Promise.all([
            this._super(...arguments),
            this._getTrackSuggestion()
        ]);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _submitQuiz: function () {
        var self = this;
        return this._super(...arguments).then(function (data) {
            if (data.quiz_completed) {
                self.$('.o_quiz_js_quiz_next_track')
                    .removeClass('btn-light')
                    .addClass('btn-secondary');
            }

            return Promise.resolve(data);
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _getTrackSuggestion: function () {
        var self = this;
        return this.rpc('/event_track/get_track_suggestion', {
            track_id: this.track.id,
        }).then(function (suggestion) {
            self.nextSuggestion = suggestion;
            return Promise.resolve();
        });
    }
});

export default WebsiteEventTrackSuggestionQuiz;
