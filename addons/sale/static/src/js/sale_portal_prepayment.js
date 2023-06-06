/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.PortalPrepayment = publicWidget.Widget.extend({
    selector: '.o_portal_sale_sidebar',
    events: Object.assign({}, publicWidget.Widget.prototype.events, {
        'click button[name="o_sale_portal_amount_prepayment_button"]': '_onClickAmountPrepaymentButton',
        'click button[name="o_sale_portal_amount_total_button"]': '_onClickAmountTotalButton',
    }),

    start: async function () {
        this.AmountTotalButton = document.querySelector(
            'button[name="o_sale_portal_amount_total_button"]'
        );
        this.AmountPrepaymentButton = document.querySelector(
            'button[name="o_sale_portal_amount_prepayment_button"]'
        );

        if (!this.AmountTotalButton) {
            // Button not available in dom => confirmed SO or partial payment not enabled on this SO
            // this widget has nothing to manage
            return;
        }

        const params = new URLSearchParams(window.location.search);
        const isPartialPayment = params.has('downpayment') ? params.get('downpayment') === 'true': true;
        const showPaymentModal = params.get('showPaymentModal') === 'true';

        // Prepare the modal to show if the down payment amount is selected or not.
        if (isPartialPayment) {
            this._onClickAmountPrepaymentButton(false);
        } else {
            this._onClickAmountTotalButton(false);
        }

        // When updating the amount re-open the modal.
        if (showPaymentModal) {
            const payNowButton = this.$('#o_sale_portal_paynow')[0];
            payNowButton && payNowButton.click();
        }
    },

    _onClickAmountPrepaymentButton: function (doReload=true) {
        this.AmountTotalButton?.classList.add('opacity-50');
        this.AmountPrepaymentButton?.classList.remove('opacity-50');

        if (doReload) {
            this._reloadAmount(true);
        } else {
            this.$('div[id="o_sale_portal_use_amount_total"]').hide();
            this.$('div[id="o_sale_portal_use_amount_prepayment"]').show();
        }
    },

    _onClickAmountTotalButton: function(doReload=true) {
        this.AmountTotalButton?.classList.remove('opacity-50');
        this.AmountPrepaymentButton?.classList.add('opacity-50');

        if (doReload) {
            this._reloadAmount(false);
        } else {
            this.$('div[id="o_sale_portal_use_amount_total"]').show();
            this.$('div[id="o_sale_portal_use_amount_prepayment"]').hide();
        }
    },

    _reloadAmount: function (partialPayment) {
        const searchParams = new URLSearchParams(window.location.search);

        if (partialPayment) {
            searchParams.set('downpayment', true);
        } else {
            searchParams.set('downpayment', false);
        }
        searchParams.set('showPaymentModal', true);

        window.location.search = searchParams.toString();
    },
});
export default publicWidget.registry.PortalPrepayment;
