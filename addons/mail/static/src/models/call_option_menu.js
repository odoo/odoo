/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'CallOptionMenu',
    identifyingFields: ['callActionListView'],
    recordMethods: {
        /**
         * @param {Event} ev
         */
        onChangeVideoFilterCheckbox(ev) {
            const filterVideoGrid = ev.target.checked;
            const activeRtcSession = this.callActionListView.callView.activeRtcSession;
            if (filterVideoGrid && activeRtcSession && !activeRtcSession.videoStream) {
                this.callActionListView.callView.update({ activeRtcSession: clear() });
            }
            this.callActionListView.callView.update({ filterVideoGrid });
        },
        /**
         * Creates and download a file that contains the logs of the current RTC call.
         *
         * @param {MouseEvent} ev
         */
        async onClickDownloadLogs(ev) {
            const channel = this.callActionListView.callView.threadView.thread;
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
            this.callActionListView.callView.activateFullScreen();
            this.component.trigger('o-popover-close');
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickDeactivateFullScreen(ev) {
            this.callActionListView.callView.deactivateFullScreen();
            this.component.trigger('o-popover-close');
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickOptions(ev) {
            this.messaging.userSetting.callSettingsMenu.toggle();
            this.component.trigger('o-popover-close');
        },
    },
    fields: {
        /**
         * States the OWL component of this option list.
         */
        component: attr(),
        callActionListView: one('CallActionListView', {
            inverse: 'callOptionMenu',
            readonly: true,
            required: true,
        }),
    },
});
