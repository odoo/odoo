/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MailTemplateView extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {MailTemplateView}
     */
    get mailTemplateView() {
        return this.props.record;
    }

}

Object.assign(MailTemplateView, {
    props: { record: Object },
    template: 'mail.MailTemplateView',
});

registerMessagingComponent(MailTemplateView);
