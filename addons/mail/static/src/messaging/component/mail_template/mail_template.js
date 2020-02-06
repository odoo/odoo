odoo.define('mail.messaging.component.MailTemplate', function (require) {
'use strict';

const useStore = require('mail.messaging.component_hook.useStore');

const { Component } = owl;

class MailTemplate extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useStore(props => {
            return {
                activity: this.env.entities.Activity.get(props.activityLocalId),
                mailTemplate: this.env.entities.MailTemplate.get(props.mailTemplateLocalId),
            };
        });
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.messaging.entity.Activity}
     */
    get activity() {
        return this.env.entities.Activity.get(this.props.activityLocalId);
    }

    /**
     * @returns {mail.messaging.entity.MailTemplate}
     */
    get mailTemplate() {
        return this.env.entities.MailTemplate.get(this.props.mailTemplateLocalId);
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
    template: 'mail.messaging.component.MailTemplate',
});

return MailTemplate;

});
