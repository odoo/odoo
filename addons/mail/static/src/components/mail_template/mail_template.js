/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MailTemplate extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {MailTemplateView}
     */
    get mailTemplateView() {
        return this.messaging && this.messaging.models['MailTemplateView'].get(this.props.localId);
    }

}

Object.assign(MailTemplate, {
    props: { localId: String },
    template: 'mail.MailTemplate',
});

registerMessagingComponent(MailTemplate);
