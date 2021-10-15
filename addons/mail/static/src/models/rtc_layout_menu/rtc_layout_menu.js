/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

function factory(dependencies) {

    class RtcLayoutMenu extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            super._created();
            this.onClickFilter = this.onClickFilter.bind(this);
            this.onClickLayout = this.onClickLayout.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

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
        }

        /**
         * @param {MouseEvent} ev
         */
        onClickLayout(ev) {
            ev.preventDefault();
            this.messaging.userSetting.update({
                rtcLayout: ev.target.value,
            });
            this.component.trigger('dialog-closed');
        }

    }

    RtcLayoutMenu.fields = {
        component: attr(),
        callViewer: one2one('mail.rtc_call_viewer', {
            inverse: 'rtcLayoutMenu',
            readonly: true,
        }),
    };
    RtcLayoutMenu.identifyingFields = ['callViewer'];
    RtcLayoutMenu.modelName = 'mail.rtc_layout_menu';

    return RtcLayoutMenu;
}

registerNewModel('mail.rtc_layout_menu', factory);
