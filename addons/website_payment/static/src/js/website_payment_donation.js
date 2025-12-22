/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.WebsitePaymentDonation = publicWidget.Widget.extend({
    selector: '.o_donation_payment_form',
    events: {
        'focus .o_amount_input': '_onFocusAmountInput',
        'change #donation_comment_checkbox': '_onChangeDonationComment'
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onFocusAmountInput(ev) {
        const otherAmountEl = this.el.querySelector("#other_amount");
        if (otherAmountEl) {
            otherAmountEl.checked = true;
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeDonationComment(ev) {
        const donationCommentEl = this.el.querySelector('#donation_comment');
        const checked = ev.currentTarget.checked;
        donationCommentEl.classList.toggle('d-none', !checked);
        if (!checked) {
            donationCommentEl.value = "";
        }
    },
});
