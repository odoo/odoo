/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from "@mail/model/model_field_command";

import { url } from '@web/core/utils/urls';

registerModel({
    name: 'UserNotificationManager',
    recordMethods: {
        /**
         * Send a notification, preferably a native one. If native
         * notifications are disable or unavailable on the current
         * platform, fallback on the notification service.
         *
         * @param {Object} param0
         * @param {string} [param0.message] The body of the
         * notification.
         * @param {string} [param0.title] The title of the notification.
         * @param {string} [param0.type] The type to be passed to the no
         * service when native notifications can't be sent.
         * @returns
         */
        sendNotification({ message, title, type }) {
            if (!this.canSendNativeNotification) {
                this._sendOdooNotification(message, { title, type });
                return;
            }
            if (!this.messaging.env.services['multi_tab'].isOnMainTab()) {
                return;
            }
            try {
                this._sendNativeNotification(title, message);
            } catch (error) {
                // Notification without Serviceworker in Chrome Android doesn't works anymore
                // So we fallback to the notification service in this case
                // https://bugs.chromium.org/p/chromium/issues/detail?id=481856
                if (error.message.includes('ServiceWorkerRegistration')) {
                    this._sendOdooNotification(message, { title, type });
                } else {
                    throw error;
                }
            }
        },
        /**
         * Method to be called when the users click on a notification.
         *
         * @param {Event} ev
         * @param {Notification} [ev.target] The notification that have
         * been clicked.
         * @private
         */
        _onClickNotification({ target: notification }) {
            window.focus();
            notification.close();
        },
        /**
         * Send a native notification.
         *
         * @param {string} title
         * @param {string} message
         */
        _sendNativeNotification(title, message) {
            const notification = new Notification(
                // The native Notification API works with plain text and not HTML
                // unescaping is safe because done only at the **last** step
                _.unescape(title),
                {
                    body: _.unescape(message),
                    icon: this.icon,
                }
            );
            notification.addEventListener('click', this._onClickNotification);
        },
        /**
         * Send a notification through the notification service.
         *
         * @param {string} message
         * @param {Object} options
         */
        async _sendOdooNotification(message, options) {
            this.messaging.env.services['notification'].add(message, options);
            if (this.canPlayAudio && this.messaging.env.services['multi_tab'].isOnMainTab()) {
                try {
                    await this.audio.play();
                } catch {
                    // Ignore errors due to the user not having interracted
                    // with the page before playing the sound.
                }
            }
        },
    },
    fields: {
        /**
         * HTMLAudioElement used to play sound when a notification is
         * sent.
         */
        audio: attr({
            compute() {
                if (!this.canPlayAudio) {
                    return clear();
                }
                const audioElement = new Audio();
                audioElement.src = audioElement.canPlayType("audio/ogg; codecs=vorbis")
                    ? url('/mail/static/src/audio/ting.ogg')
                    : url('mail/static/src/audio/ting.mp3');
                return audioElement;
            },
        }),
        canPlayAudio: attr({
            default: typeof(Audio) !== 'undefined',
        }),
        canSendNativeNotification: attr({
            /**
             * Determines whether or not sending native notification is
             * allowed.
             */
            compute() {
                return Boolean(
                    this.messaging.browser.Notification &&
                    this.messaging.browser.Notification.permission === 'granted'
                );
            },
        }),
        /**
         * Icon to be displayed by the notification.
         */
        icon: attr({
            default: '/mail/static/src/img/odoobot_transparent.png',
        }),
    },
});
