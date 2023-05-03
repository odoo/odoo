/** @odoo-module **/

import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { renderToMarkup } from "@web/core/utils/render";
import { _t } from '@web/core/l10n/translation';
import publicWidget from '@web/legacy/js/public/public_widget';

import paymentFormMixin from '@payment/js/payment_form_mixin';
import { debounce } from '@web/core/utils/timing';

publicWidget.registry.PaymentManageForm = publicWidget.Widget.extend(paymentFormMixin, {
    selector: 'form[name="o_payment_manage"]',
    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'click div[name="o_payment_option_card"]': '_onClickPaymentOption',
        'click a[name="o_payment_icon_more"]': '_onClickMorePaymentIcons',
        'click a[name="o_payment_icon_less"]': '_onClickLessPaymentIcons',
        'click button[name="o_payment_submit_button"]': '_onClickSaveToken',
        'click button[name="o_payment_delete_token"]': '_onClickDeleteToken',
        'submit': '_onSubmit',
    }),

    /**
     * @constructor
     */
    init: function () {
        this.formType = 'manage';
        const preventDoubleClick = handlerMethod => {
            return debounce(handlerMethod, 500, true);
        };
        this._super(...arguments);
        // Prevent double-clicks and browser glitches on all inputs
        this._onClickDeleteToken = preventDoubleClick(this._onClickDeleteToken);
        this._onClickLessPaymentIcons = preventDoubleClick(this._onClickLessPaymentIcons);
        this._onClickMorePaymentIcons = preventDoubleClick(this._onClickMorePaymentIcons);
        this._onClickPaymentOption = preventDoubleClick(this._onClickPaymentOption);
        this._onClickSaveToken = preventDoubleClick(this._onClickSaveToken);
        this._onSubmit = preventDoubleClick(this._onSubmit);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Assign the token to a record.
     *
     * @private
     * @param {number} tokenId - The id of the token to assign
     * @return {undefined}
     */
    _assignToken: function (tokenId) {
        // Call the assign route to assign the token to a record
        this._rpc({
            route: this.txContext['assignTokenRoute'],
            params: {
                'access_token': this.txContext.accessToken,
                'token_id': tokenId,
            }
        }).then(() => {
            window.location = this.txContext['landingRoute'];
        }).guardedCatch(error => {
            error.event.preventDefault();
            this._displayError(
                _t("Server Error"),
                _t("We are not able to save your payment method."),
                error.message.data.message,
            );
        });
    },

    /**
     * Build and open the confirmation dialog based on the linked records' information.
     *
     * @private
     * @param {Array} linkedRecordsInfo - The list of information about linked records.
     * @param confirmCallback - The callback method called when the user clicks on the confirmation
     *                          button.
     * @return {void}
     */
    _openConfirmationDialog: function (linkedRecordsInfo, confirmCallback) {
        const body = renderToMarkup('payment.ManageFormConfirmationDialog', { linkedRecordsInfo });
        this.call('dialog', 'add', ConfirmationDialog, {
            title: _t("Warning!"),
            body,
            confirmLabel: _t("Confirm Deletion"),
            confirm: confirmCallback,
            cancel: () => {},
        });
    },

    /**
     * Search for documents linked to the token and ask the user for confirmation.
     *
     * If any such document is found, a confirmation dialog is shown.
     *
     * @private
     * @param {number} tokenId - The id of the token to delete
     * @return {undefined}
     */
    _deleteToken: function (tokenId) {
        const execute = () => {
            this._rpc({
                route: '/payment/archive_token',
                params: {
                    'token_id': tokenId,
                },
            }).then(() => {
                const $tokenCard = this.$(
                    `input[name="o_payment_radio"][data-payment-option-id="${tokenId}"]` +
                    `[data-payment-option-type="token"]`
                ).closest('div[name="o_payment_option_card"]');
                $tokenCard.siblings(`#o_payment_token_inline_manage_form_${tokenId}`).remove();
                $tokenCard.remove();
                this._disableButton(false);
            }).guardedCatch(error => {
                error.event.preventDefault();
                this._displayError(
                    _t("Server Error"),
                    _t("We are not able to delete your payment method."),
                    error.message.data.message,
                );
            });
        };

        // Fetch documents linked to the token
        this._rpc({
            model: 'payment.token',
            method: 'get_linked_records_info',
            args: [tokenId],
        }).then(linkedRecordsInfo => {
            this._openConfirmationDialog(linkedRecordsInfo, execute);
        }).guardedCatch(error => {
            this._displayError(
                _t("Server Error"),
                _t("We are not able to delete your payment method."),
                error.message.data.message,
            );
        });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Find the radio button linked to the click 'Delete' button and trigger the token deletion.
     *
     * Let `_onClickPaymentOption` select the radio button and display the inline form.
     *
     * Called when clicking on the 'Delete' button of a token.
     *
     * @private
     * @param {Event} ev
     * @return {undefined}
     */
    _onClickDeleteToken: function (ev) {
        ev.preventDefault();

        // Extract contextual values from the delete button
        const linkedRadio = $(ev.currentTarget).siblings().find('input[name="o_payment_radio"]')[0];
        const tokenId = this._getPaymentOptionIdFromRadio(linkedRadio);

        // Delete the token
        this._deleteToken(tokenId);
    },

    /**
     * Handle the creation of a new token or the assignation of a token to a record.
     *
     * Called when clicking on the 'Save Payment Method' button of when submitting the form.
     *
     * @private
     * @param {Event} ev
     * @return {undefined}
     */
    _onClickSaveToken: async function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        // Check that the user has selected a payment option
        const $checkedRadios = this.$('input[name="o_payment_radio"]:checked');
        if (!this._ensureRadioIsChecked($checkedRadios)) {
            return;
        }
        const checkedRadio = $checkedRadios[0];

        // Extract contextual values from the radio button
        const provider = this._getProviderFromRadio(checkedRadio);
        const paymentOptionId = this._getPaymentOptionIdFromRadio(checkedRadio);
        const flow = this._getPaymentFlowFromRadio(checkedRadio);

        // Save the payment method
        this._hideError(); // Don't keep the error displayed if the user is going through 3DS2
        this._disableButton(true); // Disable until it is needed again
        this.call('ui', 'block');
        if (flow !== 'token') { // Creation of a new token
            this.txContext.tokenizationRequested = true;
            this.txContext.isValidation = true;
            this._processPayment(provider, paymentOptionId, flow);
        } else if (this.txContext['allowTokenSelection']) { // Assignation of a token to a record
            this._assignToken(paymentOptionId);
        }
    },

    /**
     * Delegate the handling of the token to `_onClickSaveToken`.
     *
     * Called when submitting the form (e.g. through the Return key).
     *
     * @private
     * @param {Event} ev
     * @return {undefined}
     */
    _onSubmit: function (ev) {
        ev.stopPropagation();
        ev.preventDefault();

        this._onClickSaveToken(ev);
    },

});

export default publicWidget.registry.PaymentManageForm;
