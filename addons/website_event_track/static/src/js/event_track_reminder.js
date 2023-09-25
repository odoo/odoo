/** @odoo-module **/

import { debounce } from "@web/core/utils/timing";
import core from "@web/legacy/js/services/core";
import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";

publicWidget.registry.websiteEventTrackReminder = publicWidget.Widget.extend({
    selector: '.o_wetrack_js_reminder',
    events: {
        'click': '_onReminderToggleClick',
    },

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this._onReminderToggleClick = debounce(this._onReminderToggleClick, 500, true);
        this.rpc = this.bindService("rpc");
    },

    //--------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onReminderToggleClick: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();
        var self = this;
        var $trackLink = $(ev.currentTarget).find('i');

        if (this.reminderOn === undefined) {
            this.reminderOn = $trackLink.data('reminderOn');
        }

        var reminderOnValue = !this.reminderOn;

        this.rpc('/event/track/toggle_reminder', {
            track_id: $trackLink.data('trackId'),
            set_reminder_on: reminderOnValue,
        }).then(function (result) {
            if (result.error && result.error === 'ignored') {
                self.displayNotification({
                    type: 'info',
                    title: _t('Error'),
                    message: _t('Talk already in your Favorites'),
                });
            } else {
                self.reminderOn = reminderOnValue;
                var reminderText = self.reminderOn ? _t('Favorite On') : _t('Set Favorite');
                self.$('.o_wetrack_js_reminder_text').text(reminderText);
                self._updateDisplay();
                var message = self.reminderOn ? _t('Talk added to your Favorites') : _t('Talk removed from your Favorites');
                self.displayNotification({
                    type: 'info',
                    title: message
                });
                if (self.reminderOn) {
                    core.bus.trigger('open_notification_request', 'add_track_to_favorite', {
                        title: _t('Allow push notifications?'),
                        body: _t('You have to enable push notifications to get reminders for your favorite tracks.'),
                        delay: 0
                    });
                }
            }
        });
    },

    _updateDisplay: function () {
        var $trackLink = this.$el.find('i');
        var isReminderLight = $trackLink.data('isReminderLight');
        if (this.reminderOn) {
            $trackLink.addClass('fa-bell').removeClass('fa-bell-o');
            $trackLink.attr('title', _t('Favorite On'));

            if (!isReminderLight) {
                this.$el.addClass('btn-primary');
                this.$el.removeClass('btn-outline-primary');
            }
        } else {
            $trackLink.addClass('fa-bell-o').removeClass('fa-bell');
            $trackLink.attr('title', _t('Set Favorite'));

            if (!isReminderLight) {
                this.$el.removeClass('btn-primary');
                this.$el.addClass('btn-outline-primary');
            }
        }
    },

});

export default publicWidget.registry.websiteEventTrackReminder;
