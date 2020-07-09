odoo.define('mail/static/src/components/composer_suggested_recipient_info/composer_suggested_recipient_info.js', function (require) {
'use strict';

const useStore = require('mail/static/src/component_hooks/use_store/use_store.js');
const { Component } = owl;
const { useRef } = owl.hooks;
const { ComponentAdapter } = require('web.OwlCompatibility');

const components = {
    ComponentAdapter,
};
const viewDialogs = require('web.view_dialogs');

class ComposerSuggestedRecipient extends Component {

    constructor(...args) {
        super(...args);
        this.id = _.uniqueId();

        useStore(props => {
            const suggestedRecipient = this.env.models['mail.suggested_recipient_info'].get(props.suggestedRecipientLocalId);
            const thread = this.env.models['mail.thread'].get(props.threadLocalId);
            return {
                suggestedRecipient: suggestedRecipient ? suggestedRecipient.__state : undefined,
                thread: thread ? thread.__state : undefined,
                partner: suggestedRecipient && suggestedRecipient.partner
                    ? suggestedRecipient.partner.__state
                    : undefined,
            };
        });
        this.formViewDialog = viewDialogs.FormViewDialog;
        this.dialog = useRef('suggestedPartnerDialog_' + this.suggestedRecipient.localId);
        this.input = useRef('input');
    }

    // Public

    /**
     * @returns {mail.suggested_recipient_info}
     */
    get suggestedRecipient() {
        return this.env.models['mail.suggested_recipient_info'].get(this.props.recipientLocalId);
    }

    get thread() {
        return this.env.models['mail.thread'].get(this.props.threadLocalId);
    }

    /**
     * @returns {mail.partner}
     */
    get partner() {
        return this.env.models['mail.partner'].get(this.suggestedRecipient.partner.localId);
    }

    /**
     * @returns {string}
     */
    get PLEASE_COMPLETE_CUSTOMER_INFORMATION() {
        return this.env._t("Please complete customer's information");
    }

    // private
    /**
     * Check the additional partners (not necessary registered partners), and
     * open a popup form view for the ones who informations is missing.
     * If the partner isn't completed, it will be removed from the recipients
     *
     * @private
     */
    _preprocessSuggestedPartners() {
        if (this.dialog) {
            this.dialog.comp.widget.open();
            this.dialog.comp.widget.on('closed', this, () => this.thread.fetchUpdateSuggestedRecipients());
        }
    }

    // Handler

    /**
     * @private
     */
    _onChangeSuggestedRecipient() {
        if (!this.suggestedRecipient.partner) {
            // Disable the checkbox to avoid multiple click otherwise multiple
            // bugged modal will be open
            this.input.el.disabled = true;
            this._preprocessSuggestedPartners();
        } else {
            this.suggestedRecipient.update({
                checked: !this.suggestedRecipient.checked
            });
        }
    }
}

Object.assign(ComposerSuggestedRecipient, {
    components,
    props: {
        recipientLocalId: String,
        threadLocalId: String,
    },
    template: 'mail.ComposerSuggestedRecipient',
});

return ComposerSuggestedRecipient;
});
