/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";
import { SnippetOption } from "@web_editor/js/editor/snippets.options";
import { registerWebsiteOption } from "@website/js/editor/snippets.registry";

export class Donation extends SnippetOption {
    /**
     * @override
     */
    constructor() {
        super(...arguments);
        this.defaultDescription = _t("Add a description here");
        this.descriptions = [];
        if (this.$target[0].dataset.descriptions) {
            const descriptionEls = this.$target[0].querySelectorAll('#s_donation_description_inputs > input');
            for (const descriptionEl of descriptionEls) {
                this.descriptions.push(descriptionEl.value);
            }
        }
    }
    /**
     * @override
     */
    async willStart() {
        await super.willStart(...arguments);
        this.renderContext.showOptionDescriptions = this.$target[0].dataset.descriptions;
    }
    /**
     * @override
     */
    onBuilt() {
        this._rebuildPrefilledOptions();
        return super.onBuilt(...arguments);
    }
    /**
     * @override
     */
    cleanForSave() {
        if (!this.$target[0].dataset.descriptions) {
            this._updateDescriptions();
        }
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUI() {
        await super.updateUI(...arguments);
        this._updateDescriptions();
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Show/hide options in the page.
     *
     * @see this.selectClass for parameters
     */
    displayOptions(previewMode, widgetValue, params) {
        this.$target[0].dataset.displayOptions = widgetValue;
        if (!widgetValue && this.$target[0].dataset.customAmount === "slider") {
            this.$target[0].dataset.customAmount = "freeAmount";
        } else if (widgetValue && !this.$target[0].dataset.prefilledOptions) {
            this.$target[0].dataset.customAmount = "slider";
        }
        this._rebuildPrefilledOptions();
    }
    /**
     * Add/remove prefilled buttons.
     *
     * @see this.selectClass for parameters
     */
    togglePrefilledOptions(previewMode, widgetValue, params) {
        this.$target[0].dataset.prefilledOptions = widgetValue;
        if (!widgetValue && this.$target[0].dataset.displayOptions) {
            this.$target[0].dataset.customAmount = "slider";
        }
        this._rebuildPrefilledOptions();
    }
    /**
     * Add/remove description of prefilled buttons.
     *
     * @see this.selectClass for parameters
     */
    toggleOptionDescription(previewMode, widgetValue, params) {
        this.$target[0].dataset.descriptions = widgetValue;
        this.renderContext.showOptionDescriptions = widgetValue;
        this.renderListItems(false, this._buildPrefilledOptionsList());
    }
    /**
     * Select an amount input
     *
     * @see this.selectClass for parameters
     */
    selectAmountInput(previewMode, widgetValue, params) {
        this.$target[0].dataset.customAmount = widgetValue;
        this._rebuildPrefilledOptions();
    }
    /**
     * Apply the we-list on the target and rebuild the input(s)
     *
     * @see this.selectClass for parameters
     */
    renderListItems(previewMode, value, params) {
        const valueList = JSON.parse(value);
        const donationAmounts = [];
        this.descriptions = [];
        delete this.$target[0].dataset.donationAmounts;
        valueList.forEach((value) => {
            donationAmounts.push(value.display_name);
            if (value.secondInputText) {
                this.descriptions.push(value.secondInputText);
            }
        });
        this.$target[0].dataset.donationAmounts = JSON.stringify(donationAmounts);
        this._rebuildPrefilledOptions();
    }
    /**
     * Redraws the target whenever the list changes
     *
     * @see this.selectClass for parameters
     */
    listChanged(previewMode, value, params) {
        this._updateDescriptions();
        this._rebuildPrefilledOptions();
    }
    /**
     * @see this.selectClass for parameters
     */
    setMinimumAmount(previewMode, widgetValue, params) {
        this.$target[0].dataset.minimumAmount = widgetValue;
        const $rangeSlider = this.$('#s_donation_range_slider');
        const $amountInput = this.$('#s_donation_amount_input');
        if ($rangeSlider.length) {
            $rangeSlider[0].min = widgetValue;
        } else if ($amountInput.length) {
            $amountInput[0].min = widgetValue;
        }
    }
    /**
     * @see this.selectClass for parameters
     */
    setMaximumAmount(previewMode, widgetValue, params) {
        this.$target[0].dataset.maximumAmount = widgetValue;
        const $rangeSlider = this.$('#s_donation_range_slider');
        const $amountInput = this.$('#s_donation_amount_input');
        if ($rangeSlider.length) {
            $rangeSlider[0].max = widgetValue;
        } else if ($amountInput.length) {
            $amountInput[0].max = widgetValue;
        }
    }
    /**
     * @see this.selectClass for parameters
     */
    setSliderStep(previewMode, widgetValue, params) {
        this.$target[0].dataset.sliderStep = widgetValue;
        const $rangeSlider = this.$('#s_donation_range_slider');
        if ($rangeSlider.length) {
            $rangeSlider[0].step = widgetValue;
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        switch (methodName) {
            case 'displayOptions': {
                return this.$target[0].dataset.displayOptions;
            }
            case 'togglePrefilledOptions': {
                return this.$target[0].dataset.prefilledOptions;
            }
            case 'toggleOptionDescription': {
                return this.$target[0].dataset.descriptions;
            }
            case 'selectAmountInput': {
                return this.$target[0].dataset.customAmount;
            }
            case 'renderListItems': {
                return this._buildPrefilledOptionsList();
            }
            case 'setMinimumAmount': {
                return this.$target[0].dataset.minimumAmount;
            }
            case 'setMaximumAmount': {
                return this.$target[0].dataset.maximumAmount;
            }
            case 'setSliderStep': {
                return this.$target[0].dataset.sliderStep;
            }
        }
        return super._computeWidgetState(...arguments);
    }
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'free_amount_opt') {
            return !(this.$target[0].dataset.displayOptions && !this.$target[0].dataset.prefilledOptions);
        }
        return super._computeWidgetVisibility(...arguments);
    }
    /**
     * Build the prefilled options list in the editor panel
     *
     * @private
     */
    _buildPrefilledOptionsList() {
        const amounts = JSON.parse(this.$target[0].dataset.donationAmounts);
        let valueList = amounts.map((amount, i) => {
            let doubleInput = {};
            if (this.$target[0].dataset.descriptions) {
                doubleInput = {
                    firstInputClass: "w-25",
                    secondInputClass: "w-auto",
                    secondInputText: this.descriptions[i] || this.defaultDescription,
                }
            }
            return {
                id: amount,
                display_name: amount,
                ...doubleInput,
            };
        });
        return JSON.stringify(valueList);
    }
    /**
     * Update descriptions in the input hidden.
     *
     * @private
     */
    _updateDescriptions() {
        const descriptionInputs = this.$target.find('#s_donation_description_inputs');
        descriptionInputs.empty();
        this.descriptions.forEach((description) => {
            const inputEl = document.createElement('input');
            inputEl.type = 'hidden';
            inputEl.classList.add('o_translatable_input_hidden', 'd-block', 'mb-1', 'w-100');
            inputEl.name = 'donation_descriptions';
            inputEl.value = description;
            descriptionInputs[0].appendChild(inputEl);
        });
    }
    /**
     * Rebuild options in the DOM.
     *
     * @private
     */
    _rebuildPrefilledOptions() {
        const rebuild = this.$target[0].dataset.displayOptions;
        this.$target.find('.s_donation_prefilled_buttons').remove();
        const layout = this.$target[0].dataset.customAmount;
        const $slider = this.$target.find('.s_donation_range_slider_wrap');
        if (layout !== "slider" || !rebuild) {
            $slider.remove();
        }
        if (rebuild) {
            if (layout === "slider" && !$slider.length) {
                const sliderTemplate = $(renderToElement('website_payment.donation.slider', {
                    minimum_amount: this.$target[0].dataset.minimumAmount,
                    maximum_amount: this.$target[0].dataset.maximumAmount,
                    slider_step: this.$target[0].dataset.sliderStep,
                }));
                this.$target.find('.s_donation_donate_btn').before(sliderTemplate);
            }
            const prefilledOptions = this.$target[0].dataset.prefilledOptions;
            let donationAmounts = [];
            let showDescriptions = false;
            if (prefilledOptions) {
                donationAmounts = JSON.parse(this.$target[0].dataset.donationAmounts);
                showDescriptions = this.$target[0].dataset.descriptions;
                if (showDescriptions) {
                    const $descriptions = this.$target.find('#s_donation_description_inputs > input');
                    donationAmounts = donationAmounts.map((amount, i) => {
                        return {
                            value: amount,
                            description: $descriptions[i] ? $descriptions[i].value : this.defaultDescription,
                        };
                    });
                }
            }
            const $prefilledButtons = $(renderToElement(`website_payment.donation.prefilledButtons${showDescriptions ? 'Descriptions' : ''}`, {
                prefilled_buttons: donationAmounts,
                custom_input: layout === "freeAmount",
                minimum_amount: this.$target[0].dataset.minimumAmount,
            }));
            this.$target.find('#s_donation_description_inputs').after($prefilledButtons);
        }
    }
}
registerWebsiteOption("Donation", {
    Class: Donation,
    template: "website_payment.s_donation_options",
    selector: ".s_donation",
});
