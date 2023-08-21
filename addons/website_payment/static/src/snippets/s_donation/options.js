/** @odoo-module **/

import { renderToElement } from "@web/core/utils/render";
import options from '@web_editor/js/editor/snippets.options';
import { _t } from "@web/core/l10n/translation";

options.registry.Donation = options.Class.extend({
    /**
     * @override
     */
    start() {
        this.defaultDescription = _t("Add a description here");
        return this._super(...arguments);
    },
    /**
     * @override
     */
    onBuilt() {
        this._rebuildPrefilledOptions();
        return this._super(...arguments);
    },
    /**
     * @override
     */
    cleanForSave() {
        if (!this.$target[0].dataset.descriptions) {
            this._updateDescriptions();
        }
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async updateUI() {
        await this._super(...arguments);
        this._buildDescriptionsList();
    },

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
    },
    /**
     * Add/remove prefilled buttons.
     *
     * @see this.selectClass for parameters
     */
    togglePrefilledOptions(previewMode, widgetValue, params) {
        this.$target[0].dataset.prefilledOptions = widgetValue;
        this.$el.find('.o_we_prefilled_options_list').toggleClass('d-none', !widgetValue);
        if (!widgetValue && this.$target[0].dataset.displayOptions) {
            this.$target[0].dataset.customAmount = "slider";
        }
        this._rebuildPrefilledOptions();
    },
    /**
     * Add/remove description of prefilled buttons.
     *
     * @see this.selectClass for parameters
     */
    toggleOptionDescription(previewMode, widgetValue, params) {
        this.$target[0].dataset.descriptions = widgetValue;
        this.renderListItems(false, this._buildPrefilledOptionsList());
    },
    /**
     * Select an amount input
     *
     * @see this.selectClass for parameters
     */
    selectAmountInput(previewMode, widgetValue, params) {
        this.$target[0].dataset.customAmount = widgetValue;
        this._rebuildPrefilledOptions();
    },
    /**
     * Apply the we-list on the target and rebuild the input(s)
     *
     * @see this.selectClass for parameters
     */
    renderListItems(previewMode, value, params) {
        const valueList = JSON.parse(value);
        const donationAmounts = [];
        delete this.$target[0].dataset.donationAmounts;
        valueList.forEach((value) => {
            donationAmounts.push(value.display_name);
        });
        this.$target[0].dataset.donationAmounts = JSON.stringify(donationAmounts);
        this._rebuildPrefilledOptions();
    },
    /**
     * Redraws the target whenever the list changes
     *
     * @see this.selectClass for parameters
     */
    listChanged(previewMode, value, params) {
        this._updateDescriptions();
        this._rebuildPrefilledOptions();
    },
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
    },
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
    },
    /**
     * @see this.selectClass for parameters
     */
    setSliderStep(previewMode, widgetValue, params) {
        this.$target[0].dataset.sliderStep = widgetValue;
        const $rangeSlider = this.$('#s_donation_range_slider');
        if ($rangeSlider.length) {
            $rangeSlider[0].step = widgetValue;
        }
    },

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
        return this._super(...arguments);
    },
    /**
     * @override
     */
    async _computeWidgetVisibility(widgetName, params) {
        if (widgetName === 'free_amount_opt') {
            return !(this.$target[0].dataset.displayOptions && !this.$target[0].dataset.prefilledOptions);
        }
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _renderCustomXML(uiFragment) {
        const list = document.createElement('we-list');
        list.dataset.dependencies = "pre_filled_opt";
        list.dataset.addItemTitle = _t("Add new pre-filled option");
        list.dataset.renderListItems = '';
        list.dataset.unsortable = 'true';
        list.dataset.inputType = 'number';
        list.dataset.defaultValue = 50;
        list.dataset.listChanged = '';
        $(uiFragment).find('we-checkbox[data-name="pre_filled_opt"]').after(list);
    },
    /**
     * Build the prefilled options list in the editor panel
     *
     * @private
     */
    _buildPrefilledOptionsList() {
        const amounts = JSON.parse(this.$target[0].dataset.donationAmounts);
        let valueList = amounts.map(amount => {
            return {
                id: amount,
                display_name: amount,
            };
        });
        return JSON.stringify(valueList);
    },
    /**
     * Add descriptions in the prefilled options list of the
     * editor panel.
     *
     * @private
     */
    _buildDescriptionsList() {
        if (this.$target[0].dataset.descriptions) {
            const $descriptions = this.$target.find('#s_donation_description_inputs > input');
            const $tableEl = this.$el.find('we-list table');
            $tableEl.find("tr").toArray().forEach((trEl, i) => {
                const $inputAmount = $(trEl).find('td').first();
                $inputAmount.addClass('w-25');
                const tdEl = document.createElement('td');
                const inputEl = document.createElement('input');
                inputEl.type = 'text';
                inputEl.value = $descriptions[i] ? $descriptions[i].value : this.defaultDescription;
                tdEl.classList.add('w-auto');
                tdEl.appendChild(inputEl);
                $(tdEl).insertAfter($inputAmount);
            });
            this._updateDescriptions();
        }
    },
    /**
     * Update descriptions in the input hidden.
     *
     * @private
     */
    _updateDescriptions() {
        const descriptionInputs = this.$target.find('#s_donation_description_inputs');
        descriptionInputs.empty();
        const descriptions = this.$el.find('we-list input[type=text]');
        descriptions.toArray().forEach((description) => {
            const inputEl = document.createElement('input');
            inputEl.type = 'hidden';
            inputEl.classList.add('o_translatable_input_hidden', 'd-block', 'mb-1', 'w-100');
            inputEl.name = 'donation_descriptions';
            inputEl.value = description.value;
            descriptionInputs[0].appendChild(inputEl);
        });
    },
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
            let donationAmounts = 0;
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
    },
});

export default {
    Donation: options.registry.Donation,
};
