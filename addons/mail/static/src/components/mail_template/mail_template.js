/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MailTemplate extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {MailTemplate}
     */
    get mailTemplate() {
        return this.messaging && this.messaging.models['MailTemplate'].get(this.props.mailTemplateLocalId);
    }

    /**
     * @returns {MailTemplateView}
     */
    get mailTemplateView() {
        return this.messaging && this.messaging.models['MailTemplateView'].get(this.props.localId);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickPreview(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.mailTemplate.preview(this.mailTemplateView.activityViewOwner.activity);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSend(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.mailTemplate.send(this.mailTemplateView.activityViewOwner.activity);
    }

}

Object.assign(MailTemplate, {
    props: {
        localId: String,
        mailTemplateLocalId: String,
    },
    template: 'mail.MailTemplate',
});

registerMessagingComponent(MailTemplate);
