odoo.define('website_event_track.website_event_track_timer', function (require) {

'use strict';

const publicWidget = require('web.public.widget');

/*
 * Simple implementation of a timer widget that uses a "time to live" configuration
 * value to countdown seconds on a target element.
 * Will be used to visually countdown the time before a talk starts.
 * When the timer reaches 0, the element destroys itself.
 */
publicWidget.registry.websiteEventTrackTimer = publicWidget.Widget.extend({

    selector: '.o_we_track_timer',
    events: {
        'click .close': '_onCloseClick',
    },

    /**
     * @override
     */
    start: function () {
        return this._super.apply(this, arguments).then(() => {
            let timeToLive = this.$el.data('time-to-live');
            let deadline = moment().add(timeToLive, 'seconds');
            let remainingMs = deadline.diff(moment());
            if (remainingMs > 0) {
                this._updateTimerDisplay(remainingMs);
                this.$el.removeClass('d-none');
                this.deadline = deadline;
                this.timer = setInterval(this._refreshTimer.bind(this), 1000);
            } else {
                this.destroy();
            }
        });
    },

    /**
     * @override
     */
    destroy: function() {
        this.$el.parent().remove();
        clearInterval(this.timer);
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    _onCloseClick: function () {
        this.destroy();
    },

    /**
     * The function will trigger an update if the timer has not yet expired.
     * Otherwise, the component will be destroyed.
     */
    _refreshTimer: function () {
        let remainingMs = this.deadline.diff(moment());
        if (remainingMs > 0) {
            this._updateTimerDisplay(remainingMs);
        } else {
            this.destroy();
        }
    },

    /**
     * The function will have the responsibility to update the text indicating
     * the time remaining before the counter expires. The function will use
     * MomentJS to transform the remaining time in more a human friendly format
     * Example: "in 32 minutes", "in 17 hours", etc.
     * @param {integer} remainingMs - Time remaining before the counter expires (in ms).
     */
    _updateTimerDisplay: function (remainingMs) {
        let $timerTextEl = this.$el.find('span');
        let str = moment.duration(remainingMs, 'ms').humanize(true);
        if (str !== $timerTextEl.text()) {
            $timerTextEl.text(str);
        }
    },
});

return publicWidget.registry.websiteEventTrackTimer;

});
