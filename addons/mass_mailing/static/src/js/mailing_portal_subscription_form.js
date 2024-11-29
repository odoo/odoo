/** @odoo-module alias=mailing.PortalSubscriptionForm **/

import { rpc } from "@web/core/network/rpc";
import { renderToFragment } from "@web/core/utils/render";
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

    /**
     * @override
     * Parse start values of mailing lists subscriptions based on generated DOM
     * from server. Done here to avoid having to generate it server-side and
     * propagating it through various layers.
     */
    start: function () {
        const def = this._super.apply(this, arguments);
        this.listInfo = [...document.querySelectorAll('#o_mailing_subscription_form_manage input')].map(
            node => {
                const listInfo = {
                    id: parseInt(node.getAttribute('value')),
                    member: node.dataset.member === '1',
                    name: node.getAttribute('title'),
                    opt_out: node.getAttribute('checked') !== 'checked',
                };
                return listInfo;
            }
        );
        return def;
    },

    /*
     * Triggers call to update list subscriptions. Bubble up to let parent
     * handle returned result if necessary. RPC call returns number of optouted
     * lists, used by parent widget notably to know which feedback to ask.
     */
    _onFormSend: async function (event) {
        event.preventDefault();
        const formData = new FormData(document.querySelector('div#o_mailing_subscription_form form'));
        const mailingListOptinIds = formData.getAll('mailing_list_ids').map(id_str => parseInt(id_str));
        return await rpc(
            '/mailing/list/update',
            {
                csrf_token: formData.get('csrf_token'),
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                hash_token: this.customerData.hashToken,
                lists_optin_ids: mailingListOptinIds,
                mailing_id: this.customerData.mailingId,
            }
        ).then((result) => {
            const has_error = ['error', 'unauthorized'].includes(result);
            let callKey;
            if (has_error) {
                callKey = 'error';
            }
            else {
                callKey = (parseInt(result) > 0) ? 'subscription_updated_optout': 'subscription_updated';
                this._updateDisplay(mailingListOptinIds);
            }
            this._updateInfo(has_error ? 'error' : 'subscription_updated');
            this.trigger_up(
                'subscription_updated',
                {'callKey': callKey},
            );
        });
    },

    /**
     * Set form elements as hidden / displayed, as this form contains either an
     * informational text when being blocklisted, either the complete form to
     * manage their subscription.
     * @private
     */
    _setBlocklisted: function (isBlocklisted) {
        if (isBlocklisted) {
            document.getElementById('o_mailing_subscription_form_blocklisted').classList.remove('d-none');
            document.getElementById('o_mailing_subscription_form_manage').classList.add('d-none');
        }
        else {
            document.getElementById('o_mailing_subscription_form_blocklisted').classList.add('d-none');
            document.getElementById('o_mailing_subscription_form_manage').classList.remove('d-none');
        }
    },

    /**
     * Set form elements as readonly, e.g. when blocklisted email take precedence
     * over subscription update.
     * @private
     */
    _setReadonly: function (isReadonly) {
        const formInputNodes = document.querySelectorAll('#o_mailing_subscription_form_manage input');
        const formButtonNode = document.getElementById('button_form_send');
        if (isReadonly) {
            formInputNodes.forEach(node => {node.setAttribute('disabled', 'disabled')});
            formButtonNode.setAttribute('disabled', 'disabled');
            formButtonNode.classList.add('d-none');
        } else {
            formInputNodes.forEach(node => {node.removeAttribute('disabled')});
            formButtonNode.removeAttribute('disabled');
            formButtonNode.classList.remove('d-none');
        }
    },

    /*
     * Update display after subscription, notably to update mailing list subscription
     * status. We simply update opt_out status based on the ID being present in the
     * newly-selected opt-in mailing lists, then rerender the inputs.
     */
    _updateDisplay: function (listOptinIds) {
        /* update internal status*/
        this.listInfo.forEach(
            (listItem) => {
                listItem.member = listItem.member || listOptinIds.includes(listItem.id);
                listItem.opt_out = !listOptinIds.includes(listItem.id);
            }
        );

        /* update form of lists for update */
        const formContent = renderToFragment(
            "mass_mailing.portal.list_form_content",
            {
                listsMember: this.listInfo.filter(item => item.member === true),
                listsProposal: this.listInfo.filter(item => item.member === false),
            }
        );
        const manageForm = document.getElementById('o_mailing_subscription_form_manage');
        /*manageForm.innerHTML = formContent.innerHTML;*/
        manageForm.replaceChildren(formContent);

        /* update readonly display of customer's lists */
        const formReadonlyContent = renderToFragment(
            "mass_mailing.portal.list_form_content_readonly",
            {
                listsOptin: this.listInfo.filter(item => item.opt_out === false),
            }
        );
        const readonlyForm = document.getElementById('o_mailing_subscription_form_blocklisted');
        /*readonlyForm.innerHTML = formReadonlyContent.innerHTML;*/
        readonlyForm.replaceChildren(formReadonlyContent);
    },

    /*
     * Display feedback (visual tips) to the user concerning the last done action.
     */
    _updateInfo: function (infoKey) {
        const updateInfo = document.getElementById('o_mailing_subscription_update_info');
        if (infoKey !== undefined) {
            const infoContent = renderToFragment(
                "mass_mailing.portal.list_form_update_info",
                {
                    infoKey: infoKey,
                }
            );
            /*updateInfo.innerHTML = infoContent.innerHTML;*/
            updateInfo.replaceChildren(infoContent);
            updateInfo.classList.add(infoKey === 'error' ? 'text-danger': 'text-success');
            updateInfo.classList.remove('d-none');
        }
        else {
            updateInfo.classList.add('d-none');
        }
    },
});

export default publicWidget.registry.MailingPortalSubscriptionForm;
