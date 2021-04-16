/** @odoo-module **/

import publicWidget from 'web.public.widget';

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
        this.$target.find('#other_amount').prop("checked", true);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeDonationComment(ev) {
        const $donationComment = this.$target.find('#donation_comment');
        const checked = $(ev.currentTarget).is(':checked');
        $donationComment.toggleClass('d-none', !checked);
        if (!checked) {
            $donationComment.val('');
        }
    },
});
