/** @odoo-module **/

import { debounce } from "@web/core/utils/timing";
import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { Component } from "@odoo/owl";

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
        this.notification = this.bindService("notification");
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
        const trackLink = ev.currentTarget.querySelector("i");

        if (this.reminderOn === undefined) {
            this.reminderOn = trackLink.dataset.reminderOn;
        }

        var reminderOnValue = !this.reminderOn;

        rpc('/event/track/toggle_reminder', {
            track_id: parseInt(trackLink.dataset.trackId),
            set_reminder_on: reminderOnValue,
        }).then(function (result) {
            if (result.error && result.error === 'ignored') {
                self.notification.add(_t('Talk already in your Favorites'), {
                    type: 'info',
                    title: _t('Error'),
                });
            } else {
                self.reminderOn = reminderOnValue;
                var reminderText = self.reminderOn ? _t('Favorite On') : _t('Set Favorite');
                self.el.title = reminderText;
                self._updateDisplay();
                var message = self.reminderOn ? _t('Talk added to your Favorites') : _t('Talk removed from your Favorites');
                self.notification.add(message, {
                    type: 'info',
                });
                if (self.reminderOn) {
                    Component.env.bus.trigger('open_notification_request', [
                        'add_track_to_favorite',
                        {
                            title: _t('Allow push notifications?'),
                            body: _t('You have to enable push notifications to get reminders for your favorite tracks.'),
                            delay: 0
                        },
                    ]);
                }
            }
        });
    },

    _updateDisplay: function () {
        const trackLink = this.el.querySelector("i");
        if (this.reminderOn) {
            trackLink.classList.add("fa-bell");
            trackLink.classList.remove("fa-bell-o");
            trackLink.setAttribute("title", _t("Favorite On"));
        } else {
            trackLink.classList.add("fa-bell-o");
            trackLink.classList.remove("fa-bell");
            trackLink.setAttribute("title", _t("Set Favorite"));
        }
    },

});

export default publicWidget.registry.websiteEventTrackReminder;
