/** @odoo-module **/

import { useRefs } from '@mail/component_hooks/use_refs/use_refs';
import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class RtcOptionList extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        this._getRefs = useRefs();
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickFullScreen(ev) {
        this.messaging.userSetting.toggleFullScreen();
        this.trigger('o-popover-close');
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickLayout(ev) {
        this.messaging.userSetting.toggleLayoutSettingsWindow();
        this.trigger('o-popover-close');
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickOptions(ev) {
        this.messaging.userSetting.rtcConfigurationMenu.toggle();
        this.trigger('o-popover-close');
    }

}

Object.assign(RtcOptionList, {
    props: {},
    template: 'mail.RtcOptionList',
});

registerMessagingComponent(RtcOptionList);
