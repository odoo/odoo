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
            const payNowButton = document.querySelector('#o_sale_portal_paynow');
            payNowButton && payNowButton.click();
        }
    },

    _onClickAmountPrepaymentButton: function (doReload=true) {
        this.AmountTotalButton?.classList.remove('active');
        this.AmountPrepaymentButton?.classList.add('active');

        if (doReload) {
            this._reloadAmount(true);
        } else {
            document.querySelector('span[id="o_sale_portal_use_amount_total"]').style.display = 'none';
            document.querySelector('span[id="o_sale_portal_use_amount_prepayment"]').style.display = 'block';
        }
    },

    _onClickAmountTotalButton: function(doReload=true) {
        this.AmountPrepaymentButton?.classList.remove('active');
        this.AmountTotalButton?.classList.add('active');

        if (doReload) {
            this._reloadAmount(false);
        } else {
            document.querySelector('span[id="o_sale_portal_use_amount_total"]').style.display = 'block';
            document.querySelector('span[id="o_sale_portal_use_amount_prepayment"]').style.display = 'none';
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
