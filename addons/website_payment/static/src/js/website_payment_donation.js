import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.WebsitePaymentDonation = publicWidget.Widget.extend({
    selector: '.o_donation_payment_form',
    events: {
        'focus .o_amount_input': '_onFocusAmountInput',
        "change #donation_comment_checkbox": "_onChangeDonationComment",
        "change input[type='radio']": "_onSelectRadioButton",
        "input #other_amount_value": "_onChangeAmountInput",
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
        this._onChangeAmountInput();
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
    /**
     * Validates the custom donation amount input field.
     * Displays a warning if the input is empty, zero, or invalid.
     * Shows warnings if the amount is below the minimum or above the
     * maximum allowed.
     *
     * @private
     */
    _onChangeAmountInput() {
        const inputEl = document.querySelector("#other_amount_value");
        const warningMessageEl = document.querySelector("#warningMessageId");
        const warningMinMessageEl = document.querySelector("#warningMinMessageId");
        const value = parseFloat(inputEl.value);
        warningMessageEl.classList.toggle("d-none", value);
        warningMinMessageEl?.classList.toggle("d-none", value ? inputEl.min < value : true)
    },
    /**
     * Handles selection of donation amount options.
     * If "Other Amount" is selected, triggers validation for custom input
     * else clears the custom amount input and hides all warnings when other
     * options are chosen.
     *
     * @private
     * @param {Event} ev
     */
    _onSelectRadioButton(ev) {
        if (ev.currentTarget.id === "other_amount") {
            return this._onChangeAmountInput();
        }
        document.querySelector("#other_amount_value").value = "";
        document.querySelector("#warningMinMessageId").classList.add("d-none");
        document.querySelector("#warningMessageId").classList.add("d-none");
    },
});
