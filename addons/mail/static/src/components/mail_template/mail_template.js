odoo.define('mail/static/src/components/mail_template/mail_template.js', function (require) {
'use strict';

const useModels = require('mail/static/src/component_hooks/use_models/use_models.js');

const { Component } = owl;

class MailTemplate extends Component {

    /**
     * @override
     */
    constructor(...args) {
        super(...args);
        useModels();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @returns {mail.activity}
     */
    get activity() {
        return this.env.models['mail.activity'].get(this.props.activityLocalId);
    }

    /**
     * @returns {mail.mail_template}
     */
    get mailTemplate() {
        return this.env.models['mail.mail_template'].get(this.props.mailTemplateLocalId);
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

return MailTemplate;

});
