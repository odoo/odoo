/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

import { Component } from '@odoo/owl';

export class MailTemplate extends Component {

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

Object.assign(MailTemplate, {
    props: { record: Object },
    template: 'mail.MailTemplate',
});

registerMessagingComponent(MailTemplate);
