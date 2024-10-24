/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.WebsitePaymentDonation = publicWidget.Widget.extend({
    selector: '.o_donation_payment_form',
    events: {
        'focus .o_amount_input': '_onFocusAmountInput',
        'change #donation_comment_checkbox': '_onChangeDonationComment',
        'change input[type="radio"]': '_onSelectRadioButton',
        'input #other_amount_value': '_onChangeAmountInput',
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
     * @private
     */
    _onChangeAmountInput() {
        const inputEl = document.querySelector("#other_amount_value");
        const warningMessageEl = document.querySelector("#warningMessageId");
        const warningMinMessageEl = document.querySelector("#warningMinMessageId");
        const warningMaxMessageEl = document.querySelector("#warningMaxMessageId");
        const value = parseFloat(inputEl.value);
        warningMessageEl.classList.toggle("d-none", value);
        if (value) {
            warningMinMessageEl.classList.toggle("d-none", !(inputEl.min > value));
            if (warningMaxMessageEl) {
                warningMaxMessageEl.classList.toggle("d-none", !(inputEl.max < value));
            }
        } else {
            warningMinMessageEl.classList.add("d-none");
            if (warningMaxMessageEl) {
                warningMaxMessageEl.classList.add("d-none");
            }
        }
    },
    /**
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
        const warningMaxMessageEl = document.querySelector("#warningMaxMessageId");
        if (warningMaxMessageEl) {
            warningMaxMessageEl.classList.add("d-none");
        }
    },
});
