/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

registerModel({
    name: 'RtcOptionList',
    identifyingFields: ['rtcController'],
    lifecycleHooks: {
        _created() {
            this.onClickDownloadLogs = this.onClickDownloadLogs.bind(this);
            this.onClickActivateFullScreen = this.onClickActivateFullScreen.bind(this);
            this.onClickDeactivateFullScreen = this.onClickDeactivateFullScreen.bind(this);
            this.onClickLayout = this.onClickLayout.bind(this);
            this.onClickOptions = this.onClickOptions.bind(this);
        },
    },
    recordMethods: {
        /**
         * Creates and download a file that contains the logs of the current RTC call.
         *
         * @param {MouseEvent} ev
         */
        async onClickDownloadLogs(ev) {
            const channel = this.rtcController.callViewer.threadView.thread;
            if (!channel.rtc) {
                return;
            }
            const data = window.JSON.stringify(channel.rtc.logs);
            const blob = new window.Blob([data], { type: 'application/json' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `RtcLogs_Channel${channel.id}_Session${channel.rtc.currentRtcSession.id}_${window.moment().format('YYYY-MM-DD_HH-mm')}.json`;
            a.click();
            window.URL.revokeObjectURL(url);
            this.component.trigger('o-popover-close');
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickActivateFullScreen(ev) {
            this.rtcController.callViewer.activateFullScreen();
            this.component.trigger('o-popover-close');
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickDeactivateFullScreen(ev) {
            this.rtcController.callViewer.deactivateFullScreen();
            this.component.trigger('o-popover-close');
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickLayout(ev) {
            this.rtcController.callViewer.toggleLayoutMenu();
            this.component.trigger('o-popover-close');
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickOptions(ev) {
            this.messaging.userSetting.rtcConfigurationMenu.toggle();
            this.component.trigger('o-popover-close');
        },
    },
    fields: {
        /**
         * States the OWL component of this option list.
         */
        component: attr(),
        rtcController: one2one('RtcController', {
            inverse: 'rtcOptionList',
            readonly: true,
            required: true,
        }),
    },
});
