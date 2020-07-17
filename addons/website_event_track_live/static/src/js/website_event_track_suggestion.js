odoo.define('website_event_track.website_event_track_suggestion', function (require) {
'use strict';

var publicWidget = require('web.public.widget');

publicWidget.registry.websiteEventTrackSuggestion = publicWidget.Widget.extend({
    template: 'website_event_track_suggestion',
    xmlDependencies: ['/website_event_track_live/static/src/xml/website_event_track_live_templates.xml'],
    events: {
        'click .owevent_track_suggestion_timer': '_onTimerClick'
    },

    init: function (parent, options) {
        this._super(...arguments);

        this.name = options.name;
        this.trackUrl = options.website_url;
        this.imageSrc = options.website_image_url;
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
     * If the user clicks on the timer, stop automatic redirect.
     */
    _onTimerClick: function () {
        clearInterval(this.timerInterval);
        this.destroy();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _updateTimer: function () {
        var secondsLeft = parseInt(this.$('.owevent_track_suggestion_timer_text').text());

        if (secondsLeft > 0) {
            secondsLeft -= 1;
            this.$('.owevent_track_suggestion_timer_text').text(secondsLeft);
        }

        if (secondsLeft === 0) {
            window.location = this.trackUrl;
        }
    }
});

return publicWidget.registry.websiteEventTrackSuggestion;

});
