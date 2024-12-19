/** @odoo-module alias=mailing.PortalSubscription **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { renderToElement, renderToFragment } from "@web/core/utils/render";


publicWidget.registry.MailingPortalSubscription = publicWidget.Widget.extend({
    events: {
        'click #button_blocklist_add': '_onBlocklistAddClick',
        'click #button_blocklist_remove': '_onBlocklistRemoveClick',
        "click #button_subscription_update_preferences": "_onSendForm",
        'click #button_feedback': '_onFeedbackSendClick',
        'click .o_mailing_subscription_opt_out_reason': '_onOptOutReasonClick',
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

        // Blocklist
        this._updateDisplayBlocklist()

        // Feedback
        this.feedbackFormEl = document.getElementById('o_mailing_subscription_feedback');
        this.allowFeedback = false;
        // this.lastActionFeedback ? TODO-NAN (see controller)

        // Form
        this.listInfo = [...document.querySelectorAll('#o_mailing_subscription_form_manage input')].map(
            node => {
                const listInfo = {
                    description: node.dataset.description || '',
                    id: parseInt(node.getAttribute('value')),
                    member: node.dataset.member === '1',
                    name: node.getAttribute('title'),
                    opt_out: node.getAttribute('checked') !== 'checked',
                };
                return listInfo;
            }
        );

        this._updateDisplay();
        return this._super.apply(this, arguments);
    },

    _onActionDone: function (callKey) {
        this.lastAction = callKey;
        this._updateDisplay();
    },

    _updateDisplay: function () {
        if (this.customerData.feedbackEnabled) {
            this.feedbackFormEl.classList.remove('d-none');
        } else {
            this.feedbackFormEl.classList.add('d-none');
        }

        this._setBlocklisted(this.customerData.isBlocklisted);
        this._setReadonlyForm(this.customerData.isBlocklisted);
    
        this._setLastFeedbackAction(this.lastAction);
        this._updateDisplayFeedback(true, false);
    },

    /****************************************************
     ********** Blocklist Buttons and Message ***********
     ****************************************************/

    /*
     * Triggers call to add current email in blocklist. Update widget internals
     * and DOM accordingly (buttons display mainly).
     */
    _onBlocklistAddClick: async function (event) {
        event.preventDefault();
        return await rpc(
            '/mailing/blocklist/add',
            {
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                hash_token: this.customerData.hashToken,
                mailing_id: this.customerData.mailingId,
            }
        ).then((result) => {
            if (result === true) {
                this.customerData.isBlocklisted = true;
                this.customerData.feedbackEnabled = true;
            }
            this._updateDisplayBlocklist();
            this._updateInfoBlocklist(result === true ? 'blocklist_add' : 'error');
            this._onActionDone(result === true ? 'blocklist_add' : result);
        });
    },

    /*
     * Triggers call to remove current email from blocklist. Update widget
     * internals and DOM accordingly (buttons display mainly).
     */
    _onBlocklistRemoveClick: async function (event) {
        event.preventDefault();
        return await rpc(
            '/mailing/blocklist/remove',
            {
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                hash_token: this.customerData.hashToken,
                mailing_id: this.customerData.mailingId,
            }
        ).then((result) => {
            if (result === true) {
                this.customerData.isBlocklisted = false;
                this.customerData.feedbackEnabled = false;
            } // Note-NAN we did always write this = false in the _setBlocklistRemove method
            this._updateDisplayBlocklist();
            this._updateInfoBlocklist(result === true ? 'blocklist_remove' : 'error');
            this._onActionDone(result === true ? 'blocklist_remove' : result);
        });
    },

    /*
     * Display buttons and info according to current state. Removing from blocklist
     * is always available when being blocklisted. Adding in blocklist is available
     * when not being blocklisted, if the action is possible (valid email mainly)
     * and if the option is activated.
     */
    _updateDisplayBlocklist: function () {
        const buttonAddNode = document.getElementById('button_blocklist_add');
        const buttonRemoveNode = document.getElementById('button_blocklist_remove');
        if (this.customerData.blocklistEnabled && this.customerData.blocklistPossible && !this.customerData.isBlocklisted) {
            buttonAddNode?.classList.remove('d-none');
        } else {
            buttonAddNode?.classList.add('d-none');
        }
        if (this.customerData.isBlocklisted) {
            buttonRemoveNode.classList.remove('d-none');
        } else {
            buttonRemoveNode.classList.add('d-none');
        }
    },

    /*
     * Display feedback (visual tips) to the user concerning the last done action.
     */
    _updateInfoBlocklist: function (infoKey) {
        const updateInfo = document.getElementById('o_mailing_subscription_update_info');
        if (infoKey !== undefined) {
            const infoContent = renderToElement(
                "mass_mailing.portal.blocklist_update_info",
                {
                    infoKey: infoKey,
                }
            );
            updateInfo.innerHTML = infoContent.innerHTML;
            if (['blocklist_add', 'blocklist_remove'].includes(infoKey)) {
                updateInfo.classList.add('text-success');
                updateInfo.classList.remove('text-danger');
            }
            else {
                updateInfo.classList.add('text-danger');
                updateInfo.classList.remove('text-success');
            }
            updateInfo.classList.remove('d-none');
        }
        else {
            updateInfo.classList.add('d-none');
        }
    },

    /****************************************************
     ****************** Feedback Form *******************
     ****************************************************/

    /*
     * Triggers call to give a feedback about current subscription update.
     */
    _onFeedbackSendClick: async function (event) {
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
                this._updateDisplayFeedback(false, true);
                this._updateInfoFeedback('feedback_sent');
            }
            else {
                this._updateDisplayFeedback(false, false);
                this._updateInfoFeedback(result);
            }
            this.lastAction = result === true ? 'feedback_sent' : result;
        });
    },


   /*
    * Toggle feedback textarea display based on reason configuration
    */
   _onOptOutReasonClick: function (event) {
       this.allowFeedback = $(event.currentTarget).data('isFeedback');
       this._updateDisplayFeedback()
   },

   /*
    * Set last done action, which triggers some update in the feedback form
    * allowing to contextualize the explanation given to the customer.
    */
   _setLastFeedbackAction: function (lastAction) {
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
   _updateDisplayFeedback: function (cleanFeedback, setReadonly) {
       const feedbackArea = document.querySelector('div#o_mailing_subscription_feedback textarea');
       const feedbackButton = document.getElementById('button_feedback');
       const feedbackEl = document.getElementById('o_mailing_subscription_feedback');
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
           feedbackEl.classList.add('d-none');
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
   _updateInfoFeedback: function (infoKey) {
       const feedbackInfo = document.getElementById('o_mailing_subscription_feedback_info');
       const unsubscribedAlert = document.getElementById('o_mailing_unsubscribed_alert');
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
           unsubscribedAlert.classList.add('d-none');
       }
       else {
           feedbackInfo.classList.add('d-none');
       }
   },

    /****************************************************
     ***************** Subscription Form ****************
     ****************************************************/

    /*
     * Triggers call to update list subscriptions. Bubble up to let parent
     * handle returned result if necessary. RPC call returns number of optouted
     * lists, used by parent widget notably to know which feedback to ask.
     */
    _onSendForm: async function (event) {
        event.preventDefault();
        const selectedOptOutReason = document.querySelector('div#o_mailing_subscription_feedback form input.o_mailing_subscription_opt_out_reason:checked');
        const optoutReasonId = selectedOptOutReason ? parseInt(selectedOptOutReason.value) : null;
        const formData = new FormData(document.querySelector('div#o_mailing_subscription_form form'));
        const mailingListOptinIds = formData.getAll('mailing_list_ids').map(id_str => parseInt(id_str));
        return await rpc(
            '/mailing/list/update',
            {
                csrf_token: formData.get('csrf_token'),
                document_id: this.customerData.documentId,
                email: this.customerData.email,
                opt_out_reason_id: optoutReasonId,
                hash_token: this.customerData.hashToken,
                lists_optin_ids: mailingListOptinIds,
                mailing_id: this.customerData.mailingId,
            }
        ).then((result) => {
            const has_error = ['error', 'unauthorized'].includes(result);
            if (!has_error) {
                this._updateDisplayForm(mailingListOptinIds);
            }
            this._updateInfoForm(has_error ? 'error' : 'success');
        });
    },

    /**
     * Set form elements as hidden / displayed, as this form contains either an
     * informational text when being blocklisted, either the complete form to
     * manage their subscription.
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
     */
    _setReadonlyForm: function (isReadonly) {
        const formInputNodes = document.querySelectorAll('#o_mailing_subscription_form_manage input');
        const formButtonNodes = document.querySelectorAll('.mailing_lists_checkboxes');
        const updatePreferencesButton = document.getElementById('button_subscription_update_preferences')
        if (isReadonly) {
            formInputNodes.forEach(node => {node.setAttribute('disabled', 'disabled')});
            formButtonNodes.forEach(node => {
                node.setAttribute('disabled', 'disabled');
                node.classList.add('d-none');
            });
            updatePreferencesButton.classList.add('d-none');
        } else {
            formInputNodes.forEach(node => {node.removeAttribute('disabled')});
            formButtonNodes.forEach(node => {
                node.removeAttribute('disabled');
                node.classList.remove('d-none');
            });
            updatePreferencesButton.classList.remove('d-none');
        }
    },

    /*
     * Update display after subscription, notably to update mailing list subscription
     * status. We simply update opt_out status based on the ID being present in the
     * newly-selected opt-in mailing lists, then rerender the inputs.
     */
    _updateDisplayForm: function (listOptinIds) {
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
                email: this.customerData.email,
                listsMemberOrPoposal: this.listInfo,
            }
        );
        const manageForm = document.getElementById('o_mailing_subscription_form_manage');
        /*manageForm.innerHTML = formContent.innerHTML;*/
        manageForm.replaceChildren(formContent);

        // Handle line breaks on re-rendering text descriptions
        const listDescriptions = document.querySelectorAll('.o_mailing_subscription_form_list_description');
        listDescriptions.forEach(
            (listDescription) => {
                listDescription.innerHTML = listDescription.dataset.description.replaceAll("\n", "<br>");
            }
        )
    },

    /*
     * Display feedback (visual tips) to the user concerning the last done action.
     */
    _updateInfoForm: function (infoKey) {
        const updateInfo = document.getElementById('o_mailing_subscription_update_info');
        const infoContent = renderToFragment(
            "mass_mailing.portal.list_form_update_status",
            {
                infoKey: infoKey,
            }
        );
        updateInfo.replaceChildren(infoContent);
        updateInfo.classList.remove('d-none');

        if (infoKey === 'error') {
            updateInfo.classList.add('text-danger');
            updateInfo.classList.remove('text-success');
        } else {
            updateInfo.classList.add('text-success');
            updateInfo.classList.remove('text-danger');
        }
    },

});

export default publicWidget.registry.MailingPortalSubscription;
