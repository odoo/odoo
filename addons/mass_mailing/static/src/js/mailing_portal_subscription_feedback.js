/** @odoo-module alias=mailing.PortalSubscriptionFeedback **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import publicWidget from "@web/legacy/js/public/public_widget";
import { renderToElement } from "@web/core/utils/render";


publicWidget.registry.MailingPortalSubscriptionFeedback = publicWidget.Widget.extend({
    events: {
        'click #button_feedback': '_onFeedbackClick',
        'click .o_mailing_subscription_opt_out_reason': '_onOptOutReasonClick',
    },

    /**
     * @override
     */
    init: function (parent, options) {
        this.customerData = options.customerData;
        this.allowFeedback = false;
        this.lastAction = false;
        return this._super.apply(this, arguments);
    },

    /**
     * @override
     */
    start: function () {
        this._updateDisplay(true, false);
        return this._super.apply(this, arguments);
    },

    /*
     * Triggers call to give a feedback about current subscription update.
     * Bubble up to let parent handle returned result if necessary.
     */
    _onFeedbackClick: async function (event) {
        event.preventDefault();
        const formData = new FormData(document.querySelector('div#o_mailing_subscription_feedback form'));
        const optoutReasonId = parseInt(formData.get('opt_out_reason_id'));
        return await rpc(
            '/mailing/feedback',
            {
                csrf_token: formData.get('csrf_token'),
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                feedback: formData.get('feedback'),
                hash_token: this.customerData.hashToken,
                last_action: this.lastAction,
                mailing_id: this.customerData.mailingId,
                opt_out_reason_id: optoutReasonId,
            }
        ).then((result) => {
            if (result === true) {
                this._updateDisplay(false, true);
                this._updateInfo('feedback_sent');
            }
            else {
                this._updateDisplay(false, false);
                this._updateInfo(result);
            }
            this.trigger_up(
                'feedback_sent',
                {'callKey': result === true ? 'feedback_sent' : result},
            );
        });
    },


    /*
     * Toggle feedback textarea display based on reason configuration
     */
    _onOptOutReasonClick: function (event) {
        this.allowFeedback = $(event.currentTarget).data('isFeedback');
        this._updateDisplay()
    },

    /*
     * Set last done action, which triggers some update in the feedback form
     * allowing to contextualize the explanation given to the customer.
     */
    _setLastAction: function (lastAction) {
        this.lastAction = lastAction;
        if (this.lastAction === 'blocklist_add') {
            document.querySelector('div#o_mailing_subscription_feedback p').innerHTML = _t(
                'Please let us know why you want to be in our block list.'
            );
        }
        else {
            document.querySelector('div#o_mailing_subscription_feedback p').innerHTML = _t(
                'Please let us know why you updated your subscription.'
            );
        }
    },

    /*
     * Update display after option changes, notably feedback textarea not being
     * always accessible. Opt-out reasons are displayed only if user opt-outed
     * from some mailing lists or added their email in the blocklist.
     */
    _updateDisplay: function (cleanFeedback, setReadonly) {
        const feedbackArea = document.querySelector('div#o_mailing_subscription_feedback textarea');
        const feedbackButton = document.getElementById('button_feedback');
        const feedbackReasons = document.querySelectorAll('div#o_mailing_subscription_feedback input');
        const feedbackInfo = document.getElementById('o_mailing_subscription_feedback_info');
        if (this.allowFeedback) {
            feedbackArea.classList.remove('d-none');
        } else {
            feedbackArea.classList.add('d-none');
        }
        if (setReadonly) {
            feedbackArea.setAttribute('disabled', 'disabled');
            feedbackButton.setAttribute('disabled', 'disabled');
            feedbackReasons.forEach(node => node.setAttribute('disabled', 'disabled'));
        }
        else {
            feedbackArea.removeAttribute('disabled');
            feedbackButton.removeAttribute('disabled');
            feedbackReasons.forEach(node => node.removeAttribute('disabled'));
        }
        if (cleanFeedback) {
            feedbackArea.value = '';
            feedbackInfo.innerHTML = "";
        }
    },

    /*
     * Display feedback (visual tips) to the user concerning the last done action.
     */
    _updateInfo: function (infoKey) {
        const feedbackInfo = document.getElementById('o_mailing_subscription_feedback_info');
        if (infoKey !== undefined) {
            const infoContent = renderToElement(
                "mass_mailing.portal.feedback_update_info",
                {
                    infoKey: infoKey,
                }
            );
            feedbackInfo.innerHTML = infoContent.innerHTML;
            feedbackInfo.classList.add(infoKey === 'feedback_sent' ? 'text-success' : 'text-danger');
            feedbackInfo.classList.remove('d-none', infoKey === 'feedback_sent' ? 'text-danger': 'text-success');
        }
        else {
            feedbackInfo.classList.add('d-none');
        }
    },
});

export default publicWidget.registry.MailingPortalSubscriptionFeedback;
