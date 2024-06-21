/** @odoo-module **/

import { debounce } from "@web/core/utils/timing";
import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { Component } from "@odoo/owl";
import { getElementData } from "@web/core/utils/ui";

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
        const trackLinkEl = ev.currentTarget.querySelector("i");

        const data = getElementData(trackLinkEl);
        if (this.reminderOn === undefined) {
            this.reminderOn = data.reminderOn;
        }

        var reminderOnValue = !this.reminderOn;

        rpc('/event/track/toggle_reminder', {
            track_id: data.trackId,
            set_reminder_on: reminderOnValue,
        }).then(function (result) {
            if (result.error && result.error === 'ignored') {
                self.notification.add(_t('Talk already in your Favorites'), {
                    type: 'info',
                    title: _t('Error'),
                });
            } else {
                self.reminderOn = reminderOnValue;
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
        const trackLinkEl = this.el.querySelector("i");
        if (this.reminderOn) {
            trackLinkEl.classList.add("fa-bell");
            trackLinkEl.classList.remove("fa-bell-o");
            trackLinkEl.setAttribute("title", _t("Favorite On"));
        } else {
            trackLinkEl.classList.add("fa-bell-o");
            trackLinkEl.classList.remove("fa-bell");
            trackLinkEl.setAttribute("title", _t("Set Favorite"));
        }
    },

});

export default publicWidget.registry.websiteEventTrackReminder;
