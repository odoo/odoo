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
        'mouseover i': '_fillIcon',
        'mouseout i': '_emptyIcon'
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
        var $trackLink = $(ev.currentTarget).find('i');

        if (this.reminderOn === undefined) {
            this.reminderOn = $trackLink.data('reminderOn');
        }

        var reminderOnValue = !this.reminderOn;

        var trackId = $trackLink.data('trackId');

        if (reminderOnValue){
            this._checkEmailReminder(trackId);
        }
        else {
            this._removeReminder(trackId);
        }
    },

     _addReminder: function (trackId) {
        var self = this;
        rpc('/event/track/toggle_reminder', {
            track_id: trackId,
            set_reminder_on: true,
        }).then(function (result) {
            if (result.error && result.error === 'ignored') {
                self.notification.add(_t('Talk already in your Favorites'), {
                    type: 'info',
                    title: _t('Error'),
                });
            } else {
                self.$('.o_wetrack_js_reminder_text').text(_t('Favorite On'));
                self.reminderOn = true;
                self._updateDisplay();
                Component.env.bus.trigger('open_notification_request', [
                    'add_track_to_favorite',
                    {
                        title: _t('Allow push notifications?'),
                        body: _t('You have to enable push notifications to get reminders for your favorite tracks.'),
                        delay: 0
                    },
                ]);
            }
        });
    },

    _removeReminder: function (trackId) {
        var self = this;
        rpc('/event/track/toggle_reminder', {
            track_id: trackId,
            set_reminder_on: false,
        }).then(function (result) {
            self.$('.o_wetrack_js_reminder_text').text(_t('Set Favorite'));
            self.reminderOn = false;
            self._updateDisplay();
            self.notification.add(_t('Talk removed from your Favorites'), {
                type: 'info',
                sticky: true
            });
        });
    },

    _validateAddReminder: function (trackId) {
        this._addReminder(trackId);
        this.notification.add(_t('Track successfully added to your favorites. Check your email to add them to your agenda.'),
            {
                type: 'info',
                sticky: true,
                className: 'o_send_email_reminder_success'
            });
    },

    _sendEmailReminder: function (trackId) {
        rpc('/event/send_email_reminder',  {
            track_id: trackId,
        }).then( (result) => {
            this._validateAddReminder(trackId);
        });
    },

    _displayModalEmailReminder: function (trackId) {
        rpc('/event/display_modal_email_reminder', {
            'track_id': trackId,
        }).then( (result) => {
            var self = this;
            $('body').prepend(result);
            var modalEmailReminder = $('.o_wetrack_js_modal_email_reminder');
            modalEmailReminder.find(".o_form_button_cancel").on('click', function () {
                modalEmailReminder.remove();
            });
            modalEmailReminder.on('submit', function (ev) {
                ev.preventDefault();
                var data = Object.fromEntries(new FormData(ev.target).entries());
                rpc('/event/add_session_email_reminder', data).then( (result) => {
                    self._validateAddReminder(trackId);
                });
                modalEmailReminder.remove();
            });
        });
    },

    _checkEmailReminder: function (trackId){
        rpc('/event/has_email_reminder').then( (result) => {
            if (result.hasEmailReminder){
                this._sendEmailReminder(trackId);
            }
            else {
                this._displayModalEmailReminder(trackId);
            }
        })
    },

    _updateDisplay: function () {
        var $trackLink = this.$el.find('i');
        if (this.reminderOn) {
            $trackLink.addClass('fa-bell').removeClass('fa-bell-o');
            $trackLink.attr('title', _t('Favorite On'));
            $trackLink.data('reminder-on', 'True');
        } else {
            $trackLink.addClass('fa-bell-o').removeClass('fa-bell');
            $trackLink.attr('title', _t('Set Favorite'));
            $trackLink.removeData('reminder-on');
        }
    },

    _fillIcon: function (ev) {
        var $el = $(ev.target)
        if (!$el.data('reminder-on')){
            $el.removeClass('fa-bell-o').addClass('fa-bell');
        }
    },

    _emptyIcon: function (ev){
        var $el = $(ev.target)
        if (!$el.data('reminder-on')){
            $el.removeClass('fa-bell').addClass('fa-bell-o');
        }
    },

});

export default publicWidget.registry.websiteEventTrackReminder;
