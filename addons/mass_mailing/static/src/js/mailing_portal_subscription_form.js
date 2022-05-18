/** @odoo-module alias=mailing.PortalSubscriptionForm **/

import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";


publicWidget.registry.MailingPortalSubscriptionForm = publicWidget.Widget.extend({
    events: {
        'click #button_form_send': '_onFormSend',
    },

    /**
     * @override
     */
    init: function (parent, options) {
        this.customerData = options.customerData;
        return this._super.apply(this, arguments);
    },

    /*
     * Triggers call to update list subscriptions. Bubble up to let parent
     * handle returned result if necessary.
     */
    _onFormSend: async function (event) {
        event.preventDefault();
        const formData = new FormData(document.querySelector('div#o_mailing_subscription_form form'));
        const mailingListIds = formData.getAll('mailing_list_ids').map(id_str => parseInt(id_str));
        return await jsonrpc(
            '/mailing/list/update',
            {
                csrf_token: formData.get('csrf_token'),
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                hash_token: this.customerData.hashToken,
                mailing_id: this.customerData.mailingId,
                opt_in_ids: mailingListIds,
            }
        ).then((result) => {
            this.trigger_up(
                'subscription_updated',
                {'callKey': result === true ? 'subscription_updated' : result},
            );
        });
    },

    /**
     * Set form elements as readonly, e.g. because blocklisted email take precedence
     * @private
     */
    _setReadonly: function (isReadonly) {
        const formInputNodes = document.querySelectorAll('#o_mailing_subscription_form form input');
        const formButtonNode = document.getElementById('button_form_send');
        if (isReadonly) {
            formInputNodes.forEach(node => {node.setAttribute('disabled', 'disabled')});
            formButtonNode.setAttribute('disabled', 'disabled');
        } else {
            formInputNodes.forEach(node => {node.removeAttribute('disabled')});
            formButtonNode.removeAttribute('disabled');
        }
    },
});

export default publicWidget.registry.MailingPortalSubscriptionForm;
