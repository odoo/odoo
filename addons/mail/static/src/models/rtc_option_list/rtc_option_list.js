/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, one2one } from '@mail/model/model_field';

function factory(dependencies) {

    class RtcOptionList extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            super._created();
            this.onClickActivateFullScreen = this.onClickActivateFullScreen.bind(this);
            this.onClickDeactivateFullScreen = this.onClickDeactivateFullScreen.bind(this);
            this.onClickLayout = this.onClickLayout.bind(this);
            this.onClickOptions = this.onClickOptions.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {MouseEvent} ev
         */
        onClickActivateFullScreen(ev) {
            this.rtcController.callViewer.activateFullScreen();
            this.component.trigger('o-popover-close');
        }

        /**
         * @param {MouseEvent} ev
         */
        onClickDeactivateFullScreen(ev) {
            this.rtcController.callViewer.deactivateFullScreen();
            this.component.trigger('o-popover-close');
        }

        /**
         * @param {MouseEvent} ev
         */
        onClickLayout(ev) {
            this.rtcController.callViewer.toggleLayoutMenu();
            this.component.trigger('o-popover-close');
        }

        /**
         * @param {MouseEvent} ev
         */
        onClickOptions(ev) {
            this.messaging.userSetting.rtcConfigurationMenu.toggle();
            this.component.trigger('o-popover-close');
        }

    }

    RtcOptionList.fields = {
        /**
         * States the OWL component of this option list.
         */
        component: attr(),
        rtcController: one2one('mail.rtc_controller', {
            inverse: 'rtcOptionList',
            required: true,
        }),
    };

    RtcOptionList.modelName = 'mail.rtc_option_list';

    return RtcOptionList;
}

registerNewModel('mail.rtc_option_list', factory);
