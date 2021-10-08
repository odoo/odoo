/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

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
                    break;
            }
        }

        /**
         * @param {MouseEvent} ev
         */
        onClickLayout(ev) {
            ev.preventDefault();
            const rtcLayout = ev.target.value;
            // focusing the first available peer video if none is focused
            if (rtcLayout !== 'tiled' && this.messaging.rtc.channel && !this.messaging.focusedRtcSession) {
                for (const session of this.messaging.rtc.channel.rtcSessions) {
                    if (!session.videoStream) {
                        continue;
                    }
                    this.messaging.toggleFocusedRtcSession(session.id);
                    break;
                }
            }
            if (rtcLayout === 'tiled') {
                // in tiled mode all videos must be active simultaneously
                this.messaging.rtc.filterIncomingVideoTraffic();
            }
            this.messaging.userSetting.update({
                rtcLayout,
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
