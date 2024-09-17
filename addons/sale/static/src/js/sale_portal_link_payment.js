/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.PortalLinkPayment = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'click button[name="o_sale_portal_amount_installment_button"]': '_onClickAmountInstallmentButton',
        'click button[name="o_sale_portal_amount_confirmation_button"]': '_onClickAmountConfirmationButton',
    }),

    start: async function () {
        this.AmountInstallmentlButton = document.querySelector(
            'button[name="o_sale_portal_amount_installment_button"]'
        );
        this.AmountConfirmationButton = document.querySelector(
            'button[name="o_sale_portal_amount_confirmation_button"]'
        );

        const params = new URLSearchParams(window.location.search);
        const isLinkPayment = params.has('installment') ? params.get('installment') === 'true': true;
        const showPaymentModal = params.get('showPaymentModal') === 'true';

        // Prepare the modal to show if the down payment amount is selected or not.
        if (isLinkPayment) {
            this._onClickAmountInstallmentButton(false);
        } else {
            this._onClickAmountConfirmationButton(false);
        }

        // When updating the amount re-open the modal.
        if (showPaymentModal) {
            const payNowButton = this.$('#o_sale_portal_paynow')[0];
            payNowButton && payNowButton.click();
        }
    },

    _onClickAmountInstallmentButton: function (doReload=true) {
        this.AmountConfirmationButton?.classList.remove('active');
        this.AmountInstallmentlButton?.classList.add('active');

        if (doReload) {
            this._reloadAmount(true);
        }
    },

    _onClickAmountConfirmationButton: function(doReload=true) {
        this.AmountInstallmentlButton?.classList.remove('active');
        this.AmountConfirmationButton?.classList.add('active');

        if (doReload) {
            this._reloadAmount(false);
        } else {
            this.$('span[id="o_sale_portal_use_amount_total"]').show();
            this.$('span[id="o_sale_portal_use_amount_prepayment"]').hide();
        }
    },

    _reloadAmount: function (installment) {
        const searchParams = new URLSearchParams(window.location.search);

        if (installment) {
            searchParams.set('installment', true); //
        } else {
            searchParams.set('installment', false);
        }
        searchParams.set('showPaymentModal', true);

        window.location.search = searchParams.toString();
    },
});

export default publicWidget.registry.PortalLinkPayment;
