import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from "@web/core/network/rpc";

const CUSTOM_BUTTON_EXTRA_WIDTH = 10;
let cachedCurrency;

publicWidget.registry.DonationSnippet = publicWidget.Widget.extend({
    selector: '.s_donation',
    disabledInEditableMode: false,
    events: {
        'click .s_donation_btn': '_onClickPrefilledButton',
        // Patched in the init
        'click .s_donation_donate_btn': '_onClickDonateNowButton',
        'input #s_donation_range_slider': '_onInputRangeSlider',
    },

    /**
     * @constructor
     */
    init() {
        this._super(...arguments);
        // TODO done like this to be extra careful in stable.
        for (const [key, value] of Object.entries(this.events)) {
            if (value === '_onClickDonateNowButton') {
                this.events[key] = 'async _onClickDonateNowButtonProtected';
                break;
            }
        }
        this._currencyLoaded = new Promise(resolve => this.__confirmCurrencyLoaded = resolve);
    },

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.$rangeSlider = this.$('#s_donation_range_slider');
        this.defaultAmount = this.el.dataset.defaultAmount;
        if (this.$rangeSlider.length) {
            this.$rangeSlider.val(this.defaultAmount);
            this._setBubble(this.$rangeSlider);
        }
        await this._displayCurrencies();
        this.__confirmCurrencyLoaded();
        const customButtonEl = this.el.querySelector("#s_donation_amount_input");
        if (customButtonEl) {
            const canvasEl = document.createElement("canvas");
            const context = canvasEl.getContext("2d");
            context.font = window.getComputedStyle(customButtonEl).font;
            const width = context.measureText(customButtonEl.placeholder).width;
            customButtonEl.style.maxWidth = `${Math.ceil(width) + CUSTOM_BUTTON_EXTRA_WIDTH}px`;
        }
    },
    /**
     * @override
     */
    destroy() {
        const customButtonEl = this.el.querySelector("#s_donation_amount_input");
        if (customButtonEl) {
            customButtonEl.style.maxWidth = "";
        }
        this.$el.find('.s_donation_currency').remove();
        this._deselectPrefilledButtons();
        this.$('.alert-danger').remove();
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _deselectPrefilledButtons() {
        this.$('.s_donation_btn').removeClass('active');
    },
    /**
     * @private
     * @param {jQuery} $range
     */
    _setBubble($range) {
        const $bubble = this.$('.s_range_bubble');
        const val = $range.val();
        const min = $range[0].min || 0;
        const max = $range[0].max || 100;
        const newVal = Number(((val - min) * 100) / (max - min));
        const tipOffsetLow = 8 - (newVal * 0.16); // the range thumb size is 16px*16px. The '8' and the '0.16' are related to that 16px (50% and 1% of 16px)
        $bubble.contents().filter(function () {
            return this.nodeType === 3;
        }).replaceWith(val);

        // Sorta magic numbers based on size of the native UI thumb (source: https://css-tricks.com/value-bubbles-for-range-inputs/)
        $bubble[0].style.insetInlineStart = `calc(${newVal}% + (${tipOffsetLow}px))`;
    },
    /**
     * @private
     */
    _displayCurrencies() {
        return this._getCachedCurrency().then((result) => {
            // No need to recreate the elements if the currency is already set.
            if (this.currency === result) {
                return;
            }
            this.currency = result;
            this.$('.s_donation_currency').remove();
            const $prefilledButtons = this.$('.s_donation_btn, .s_range_bubble');
            $prefilledButtons.toArray().forEach((button) => {
                const before = result.position === "before";
                const $currencySymbol = document.createElement('span');
                $currencySymbol.innerText = result.symbol;
                $currencySymbol.classList.add('s_donation_currency', before ? "pe-1" : "ps-1");
                if (before) {
                    $(button).prepend($currencySymbol);
                } else {
                    $(button).append($currencySymbol);
                }
            });
        });
    },
    /**
     * @private
     */
    _getCachedCurrency() {
        return cachedCurrency
            ? Promise.resolve(cachedCurrency)
            : rpc("/website/get_current_currency").then((result) => {
                cachedCurrency = result;
                return result;
            });
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClickPrefilledButton(ev) {
        const $button = $(ev.currentTarget);
        this._deselectPrefilledButtons();
        $button.addClass('active');
        if (this.$rangeSlider.length) {
            this.$rangeSlider.val($button[0].dataset.donationValue);
            this._setBubble(this.$rangeSlider);
        }
    },
    /**
     * @todo in master, just merge with _onClickDonateNowButton
     */
    async _onClickDonateNowButtonProtected(ev) {
        await this._currencyLoaded;
        return this._onClickDonateNowButton(ev);
    },
    /**
     * @private
     */
    _onClickDonateNowButton(ev) {
        if (this.editableMode) {
            return;
        };
        this.$('.alert-danger').remove();
        const $buttons = this.$('.s_donation_btn');
        const $selectedButton = $buttons.filter('.active');
        let amount = $selectedButton.length ? $selectedButton[0].dataset.donationValue : 0;
        if (this.el.dataset.displayOptions && !amount) {
            if (this.$rangeSlider.length) {
                amount = this.$rangeSlider.val();
            } else if ($buttons.length) {
                amount = parseFloat(this.$('#s_donation_amount_input').val());
                let errorMessage = '';
                const minAmount = parseFloat(this.el.dataset.minimumAmount);
                if (!amount) {
                    errorMessage = _t("Please select or enter an amount");
                } else if (amount < minAmount) {
                    errorMessage = _t(
                        "The minimum donation amount is %(amount)s",
                        {
                            amount: formatCurrency(minAmount, this.currency.id),
                        }
                    );
                }
                if (errorMessage) {
                    $(ev.currentTarget).before($('<p>', {
                        class: 'alert alert-danger',
                        text: errorMessage,
                    }));
                    return;
                }
            }
        }
        if (!amount) {
            amount = this.defaultAmount;
        }
        const $form = this.$('.s_donation_form');
        $('<input>').attr({type: 'hidden', name: 'amount', value: amount}).appendTo($form);
        $('<input>').attr({type: 'hidden', name: 'currency_id', value: this.currency.id}).appendTo($form);
        $('<input>').attr({type: 'hidden', name: 'csrf_token', value: odoo.csrf_token}).appendTo($form);
        $('<input>').attr({type: 'hidden', name: 'donation_options', value: JSON.stringify(this.el.dataset)}).appendTo($form);
        $form.submit();
    },
    /**
     * @private
     */
    _onInputRangeSlider(ev) {
        this._deselectPrefilledButtons();
        this._setBubble($(ev.currentTarget));
    },
});

export default {
    DonationSnippet: publicWidget.registry.DonationSnippet,
};
