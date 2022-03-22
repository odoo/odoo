/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'RtcLayoutMenu',
    identifyingFields: ['callViewer'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickFilter(ev) {
            ev.preventDefault();
            switch (ev.target.value) {
                case 'all':
                    this.callViewer.update({
                        filterVideoGrid: false,
                    });
                    break;
                case 'video':
                    this.callViewer.update({
                        filterVideoGrid: true,
                    });
                    if (this.messaging.focusedRtcSession && !this.messaging.focusedRtcSession.videoStream) {
                        this.messaging.update({ focusedRtcSession: clear() });
                    }
                    break;
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickLayout(ev) {
            ev.preventDefault();
            this.messaging.userSetting.update({
                rtcLayout: ev.target.value,
            });
            this.component.trigger('dialog-closed');
        },
    },
    fields: {
        component: attr(),
        callViewer: one('RtcCallViewer', {
            inverse: 'rtcLayoutMenu',
            readonly: true,
        }),
    },
});
