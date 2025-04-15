/** @odoo-module alias=mailing.PortalSubscription **/

import publicWidget from "@web/legacy/js/public/public_widget";


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
        this.lastAction = this.customerData.lastAction;

        // nodes for widgets (jquery due to widget implementation)
        this.$bl_elem = this.$('#o_mailing_subscription_blocklist');
        this.$feedback_elem = this.$('#o_mailing_subscription_feedback');
        this.$form_elem = this.$('#o_mailing_subscription_form');

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
            this.feedbackWidget._setLastAction(this.lastAction);
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
        this._updateDisplay();
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
            this.customerData.feedbackEnabled = false;
        }
        this._onActionDone(callKey);
    },

    _onFeedbackSent: function (event) {
        const callKey = event.data.callKey;
        this.lastAction = callKey;
    },

    _onSubscriptionUpdated: function (event) {
        const callKey = event.data.callKey;
        if (callKey === 'subscription_updated_optout') {
            this.customerData.feedbackEnabled = true;
        }
        else if (callKey === 'subscription_updated') {
            this.customerData.feedbackEnabled = false;
        }
        this._onActionDone(callKey);
    },

    _updateDisplay: function () {
        if (! this.customerData.feedbackEnabled && this.$feedback_elem.length) {
            this.$feedback_elem.addClass('d-none');
        } else if (this.$feedback_elem.length) {
            this.$feedback_elem.removeClass('d-none');
        }
        if (this.formWidget) {
            this.formWidget._setBlocklisted(this.customerData.isBlocklisted);
            this.formWidget._setReadonly(this.customerData.isBlocklisted);
        }
        if (this.feedbackWidget) {
            this.feedbackWidget._setLastAction(this.lastAction);
            this.feedbackWidget._updateDisplay(true, false);
        }
    },
});

export default publicWidget.registry.MailingPortalSubscription;
