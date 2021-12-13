/** @odoo-module **/

import { registerMessagingComponent } from '@mail/utils/messaging_component';

const { Component } = owl;

export class MailTemplate extends Component {

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {Activity}
     */
    get activity() {
        return this.messaging && this.messaging.models['Activity'].get(this.props.activityLocalId);
    }

    /**
     * @returns {MailTemplate}
     */
    get mailTemplate() {
        return this.messaging && this.messaging.models['MailTemplate'].get(this.props.mailTemplateLocalId);
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
        this.mailTemplate.preview(this.activity);
    }

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickSend(ev) {
        ev.stopPropagation();
        ev.preventDefault();
        this.mailTemplate.send(this.activity);
    }

}

Object.assign(MailTemplate, {
    props: {
        activityLocalId: String,
        mailTemplateLocalId: String,
    },
    template: 'mail.MailTemplate',
});

registerMessagingComponent(MailTemplate);
