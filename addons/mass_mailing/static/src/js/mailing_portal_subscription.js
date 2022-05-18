/** @odoo-module alias=mailing.PortalSubscription **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { markup } from "@odoo/owl";
import { _t } from '@web/core/l10n/translation';


publicWidget.registry.MailingPortalSubscription = publicWidget.Widget.extend({
    custom_events: {
        'blocklist_add': '_onBlocklistAdd',
        'blocklist_remove': '_onBlocklistRemove',
        'feedback_sent': '_onFeedbackSent',
        'subscription_updated': '_onSubscriptionUpdated',
    },
    selector: '#o_mailing_portal_subscription',

    /**
     * @override
     */
    start: function () {
        this.customerData = {...document.getElementById('o_mailing_portal_subscription').dataset};
        this.customerData.documentId = parseInt(this.customerData.documentId || 0);
        this.customerData.mailingId = parseInt(this.customerData.mailingId || 0);
        this.customerData.feedbackEnabled = true;

        // nodes for widgets (jquery due to widget implementation)
        this.$bl_elem = this.$('#o_mailing_subscription_blocklist');
        this.$feedback_elem = this.$('#o_mailing_subscription_feedback');
        this.$form_elem = this.$('#o_mailing_subscription_form');
        // nodes for text / ui update
        this.subscriptionInfoNode = document.getElementById('o_mailing_subscription_info');
        this.subscriptionInfoStateNode = document.getElementById('o_mailing_subscription_info_state');

        this._attachBlocklist();
        this._attachFeedback();
        this._attachForm();
        this._updateDisplay();
        return this._super.apply(this, arguments);
    },

    _attachBlocklist: function () {
        if (this.$bl_elem.length) {
            this.blocklistWidget = new publicWidget.registry.MailingPortalSubscriptionBlocklist(
                this,
                {customerData: this.customerData}
            );
            this.blocklistWidget.attachTo(this.$bl_elem);
        }
    },

    _attachFeedback: function () {
        if (this.$feedback_elem.length) {
            this.feedbackWidget = new publicWidget.registry.MailingPortalSubscriptionFeedback(
                this,
                {customerData: this.customerData}
            );
            this.feedbackWidget.attachTo(this.$feedback_elem);
        }
    },

    _attachForm: function () {
        if (this.$form_elem.length) {
            this.formWidget = new publicWidget.registry.MailingPortalSubscriptionForm(
                this,
                {customerData: this.customerData}
            );
            this.formWidget.attachTo(this.$form_elem);
        }
    },

    _onActionDone: function (callKey) {
        this.lastAction = callKey;
        this._updateDisplay(callKey);
        this._updateSubscriptionInfo(callKey);
    },

    _onBlocklistAdd: function (event) {
        const callKey = event.data.callKey;
        this.customerData.isBlocklisted = event.data.isBlocklisted;
        if (callKey === 'blocklist_add') {
            this.customerData.feedbackEnabled = true;
        }
        this._onActionDone(callKey);
    },

    _onBlocklistRemove: function (event) {
        const callKey = event.data.callKey;
        this.customerData.isBlocklisted = false;
        if (callKey === 'blocklist_remove') {
            this.customerData.feedbackEnabled = true;
        }
        this._onActionDone(callKey);
    },

    _onFeedbackSent: function (event) {
        const callKey = event.data.callKey;
        if (callKey === 'feedback_sent') {
            this.customerData.feedbackEnabled = true;
        }
        this._onActionDone(callKey);
    },

    _onSubscriptionUpdated: function (event) {
        const callKey = event.data.callKey;
        if (callKey === 'subscription_updated') {
            this.customerData.feedbackEnabled = true;
        }
        this._onActionDone(callKey);
    },

    _updateDisplay: function (callKey) {
        if (! this.customerData.feedbackEnabled && this.$feedback_elem.length) {
            this.$feedback_elem.hide();
        } else if (this.$feedback_elem.length) {
            this.$feedback_elem.show();
        }
        if (this.formWidget) {
            this.formWidget._setReadonly(this.customerData.isBlocklisted);
        }
        if (this.feedbackWidget) {
            this.feedbackWidget._updateDisplay(true);
        }
    },

    _updateSubscriptionInfo: function (callKey) {
        if (callKey === 'blocklist_add') {
            this.subscriptionInfoStateNode.innerHTML = markup(
                _t('You have been successfully <strong>added to our blocklist</strong>. You will not be contacted anymore by our services.')
            );
            this.subscriptionInfoNode.setAttribute('class', 'alert alert-success');
        } else if (callKey === 'blocklist_remove') {
            this.subscriptionInfoStateNode.innerHTML = markup(
                _t('You have been successfully <strong>removed from our blocklist</strong>. You are now able to be contacted by our services.')
            );
            this.subscriptionInfoNode.setAttribute('class', 'alert alert-success');
        } else if (callKey == 'feedback_sent') {
            this.subscriptionInfoStateNode.innerHTML = _t('Thanks for your feedback.');
        } else if (callKey === 'subscription_updated') {
            this.subscriptionInfoStateNode.innerHTML = markup(
                _t('You have successfully <strong>updated your memberships.</strong>')
            );
            this.subscriptionInfoNode.setAttribute('class', 'alert alert-success');
        } else if (callKey === 'unauthorized') {
            this.subscriptionInfoStateNode.innerHTML = _t('You are not authorized to do this.');
            this.subscriptionInfoNode.setAttribute('class', 'alert alert-error');
        } else if (callKey === 'error') {
            this.subscriptionInfoStateNode.innerHTML = _t('An error occurred. Please try again later or contact us.');
            this.subscriptionInfoNode.setAttribute('class', 'alert alert-error');
        } else {
            this.subscriptionInfoStateNode.setAttribute('class', 'd-none');
        }
    },
});

export default publicWidget.registry.MailingPortalSubscription;
