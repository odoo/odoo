import { SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { renderToElement, renderToFragment } from "@web/core/utils/render";

class DonationOptionPlugin extends Plugin {
    static id = "DonationOption";
    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC, {
                template: "website_payment.DonationOption",
                selector: ".s_donation",
                // TODO AGAU: remove when merging https://github.com/odoo-dev/odoo/pull/4240
                cleanForSave: this.cleanForSave.bind(this),
            }),
        ],
        builder_actions: {
            toggleDisplayOptions: this.makeToggleDataAttributeAction(
                "displayOptions",
                this.toggleDisplayOptions.bind(this)
            ),
            togglePrefilledOptions: this.makeToggleDataAttributeAction(
                "prefilledOptions",
                this.togglePrefilledOptions.bind(this)
            ),
            toggleDescriptions: this.makeToggleDataAttributeAction(
                "descriptions",
                this.toggleDescriptions.bind(this)
            ),
            setPrefilledOptions: {
                getValue: this.getPrefilledOptionsList.bind(this),
                apply: this.applyPrefilledOptionsList.bind(this),
            },
            selectAmountInput: {
                isApplied: this.isAmountInputApplied.bind(this),
                apply: this.setAmountInput.bind(this),
            },
            setMinimumAmount: {
                getValue: this.getMinimumAmount.bind(this),
                apply: this.setMinimumAmount.bind(this),
            },
            setMaximumAmount: {
                getValue: this.getMaximumAmount.bind(this),
                apply: this.setMaximumAmount.bind(this),
            },
            setSliderStep: {
                getValue: this.getSliderStep.bind(this),
                apply: this.setSliderStep.bind(this),
            },
        },
    };

    makeToggleDataAttributeAction(dataAttributeName, toggleFunction) {
        return {
            isApplied: ({ editingElement }) => !!editingElement.dataset[dataAttributeName],
            apply: (obj, ...restArgs) => {
                const { editingElement } = obj;
                editingElement.dataset[dataAttributeName] = "true";
                toggleFunction({ ...obj, value: true }, ...restArgs);
            },
            clean: (obj, ...restArgs) => {
                const { editingElement } = obj;
                delete editingElement.dataset[dataAttributeName];
                toggleFunction({ ...obj, value: false }, ...restArgs);
            },
        };
    }

    toggleDisplayOptions({ editingElement, value }) {
        if (!value && editingElement.dataset.customAmount === "slider") {
            editingElement.dataset.customAmount = "freeAmount";
        } else if (value && !editingElement.dataset.prefilledOptions) {
            editingElement.dataset.customAmount = "slider";
        }
        this.rebuildPrefilledOptions(editingElement);
    }

    togglePrefilledOptions({ editingElement, value }) {
        if (!value && editingElement.dataset.displayOptions) {
            editingElement.dataset.customAmount = "slider";
        }
        this.rebuildPrefilledOptions(editingElement);
    }

    toggleDescriptions({ editingElement }) {
        this.rebuildPrefilledOptions(editingElement);
    }

    getPrefilledOptionsList({ editingElement }) {
        const savedOptions = editingElement.dataset.prefilledOptionsList;

        // TODO AGAU: remove when merging https://github.com/odoo-dev/odoo/pull/4240
        {
            if (savedOptions) {
                return savedOptions;
            } else {
                const options = [];
                const amounts = JSON.parse(editingElement.dataset.donationAmounts || "[]");
                const descriptionEls = editingElement.querySelectorAll(
                    "#s_donation_description_inputs input"
                );
                const descriptions = Array.from(descriptionEls).map(
                    (descriptionEl) => descriptionEl.value
                );
                for (let i = 0; i < amounts.length; i++) {
                    options.push({
                        value: amounts[i],
                        description:
                            typeof descriptions[i] === "string"
                                ? descriptions[i]
                                : _t("Add a description here"),
                    });
                }
                return JSON.stringify(options);
            }
        }

        // TODO AGAU: uncomment when merging https://github.com/odoo-dev/odoo/pull/4240
        // return savedOptions || "[]";
    }

    applyPrefilledOptionsList({ editingElement, value }) {
        // TODO AGAU: remove when merging https://github.com/odoo-dev/odoo/pull/4240
        {
            const options = JSON.parse(value);
            const amounts = options.map((option) => option.value);
            editingElement.dataset.donationAmounts = JSON.stringify(amounts);
        }

        editingElement.dataset.prefilledOptionsList = value;
        this.rebuildPrefilledOptions(editingElement, value);
    }

    isAmountInputApplied({ editingElement, params }) {
        return editingElement.dataset.customAmount === params.mainParam;
    }

    setAmountInput({ editingElement, params }) {
        editingElement.dataset.customAmount = params.mainParam;
        this.rebuildPrefilledOptions(editingElement);
    }

    getMinimumAmount({ editingElement }) {
        return editingElement.dataset.minimumAmount;
    }

    setMinimumAmount({ editingElement, value }) {
        editingElement.dataset.minimumAmount = value;
        const rangeSliderEl = editingElement.querySelector("#s_donation_range_slider");
        const amountInputEl = editingElement.querySelector("#s_donation_amount_input");
        if (rangeSliderEl) {
            rangeSliderEl.min = value;
        } else if (amountInputEl) {
            amountInputEl.min = value;
        }
    }

    getMaximumAmount({ editingElement }) {
        return editingElement.dataset.maximumAmount;
    }

    setMaximumAmount({ editingElement, value }) {
        editingElement.dataset.maximumAmount = value;
        const rangeSliderEl = editingElement.querySelector("#s_donation_range_slider");
        const amountInputEl = editingElement.querySelector("#s_donation_amount_input");
        if (rangeSliderEl) {
            rangeSliderEl.max = value;
        } else if (amountInputEl) {
            amountInputEl.max = value;
        }
    }

    getSliderStep({ editingElement }) {
        return editingElement.dataset.sliderStep;
    }

    setSliderStep({ editingElement, value }) {
        editingElement.dataset.sliderStep = value;
        const rangeSliderEl = editingElement.querySelector("#s_donation_range_slider");
        if (rangeSliderEl) {
            rangeSliderEl.step = value;
        }
    }

    // TODO AGAU: remove when merging https://github.com/odoo-dev/odoo/pull/4240
    cleanForSave(editingElement) {
        delete editingElement.dataset.prefilledOptionsList;
    }

    rebuildPrefilledOptions(editingElement, options) {
        if (!options) {
            options = this.getPrefilledOptionsList({ editingElement });
        }

        // TODO AGAU: remove when merging https://github.com/odoo-dev/odoo/pull/4240
        editingElement.dataset.prefilledOptionsList = options;

        options = JSON.parse(options);

        const displayOptions = editingElement.dataset.displayOptions;
        const formEl = editingElement.querySelector(".s_donation_form");
        const donateButtonEl = editingElement.querySelector(".s_donation_donate_btn");
        const prefilledOptions = editingElement.dataset.prefilledOptions;
        const showDescriptions = prefilledOptions && editingElement.dataset.descriptions;

        // Slider
        const layout = editingElement.dataset.customAmount;
        const sliderEl = editingElement.querySelector(".s_donation_range_slider_wrap");
        if (layout !== "slider" || !displayOptions) {
            sliderEl?.remove();
        } else if (layout === "slider" && displayOptions && !sliderEl) {
            const sliderEl = renderToElement("website_payment.donation.slider", {
                minimum_amount: editingElement.dataset.minimumAmount,
                maximum_amount: editingElement.dataset.maximumAmount,
                slider_step: editingElement.dataset.sliderStep,
            });
            formEl.insertBefore(sliderEl, donateButtonEl);
        }

        // Hidden inputs for descriptions translation
        const descriptionInputContainerEl = editingElement.querySelector(
            "#s_donation_description_inputs"
        );
        descriptionInputContainerEl.innerHTML = "";
        if (showDescriptions) {
            descriptionInputContainerEl.insertBefore(
                renderToFragment("website_payment.donation.descriptionTranslationInputs", {
                    descriptions: options.map((option) => option.description),
                }),
                null
            );
        }

        // Displayed prefilled options
        editingElement.querySelector(".s_donation_prefilled_buttons")?.remove();
        if (displayOptions) {
            // TODO AGAU: remove when merging https://github.com/odoo-dev/odoo/pull/4240
            {
                if (!showDescriptions) {
                    options = options.map((option) => option.value);
                }
            }

            const prefilledButtonsEl = renderToElement(
                `website_payment.donation.prefilledButtons${
                    showDescriptions ? "Descriptions" : ""
                }`,
                {
                    prefilled_buttons: prefilledOptions ? options : [],
                    custom_input: layout === "freeAmount",
                    minimum_amount: editingElement.dataset.minimumAmount,
                }
            );
            formEl.insertBefore(prefilledButtonsEl, descriptionInputContainerEl.nextSibling);
        }
    }
}
registry.category("website-plugins").add(DonationOptionPlugin.id, DonationOptionPlugin);
