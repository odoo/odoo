import { BuilderAction } from "@html_builder/core/builder_action";
import { BaseOptionComponent } from "@html_builder/core/utils";
import { SNIPPET_SPECIFIC } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { renderToElement, renderToFragment } from "@web/core/utils/render";

export class DonationOption extends BaseOptionComponent {
    static template = "website_payment.DonationOption";
    static selector = ".s_donation";
    // TODO AGAU: remove when merging https://github.com/odoo-dev/odoo/pull/4240
    static cleanForSave(editingElement) {
        delete editingElement.dataset.prefilledOptionsList;
    }
}

export class DonationOptionPlugin extends Plugin {
    static id = "donationOption";

    resources = {
        builder_options: [
            withSequence(SNIPPET_SPECIFIC, DonationOption),
        ],
        builder_actions: {
            ToggleDisplayOptionsAction,
            TogglePrefilledOptionsAction,
            ToggleDescriptionsAction,
            SetPrefilledOptionsAction,
            SelectAmountInputAction,
            SetMinimumAmountAction,
            SetMaximumAmountAction,
            SetSliderStepAction,
        },
    };
}

export class BaseDonationAction extends BuilderAction {
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
        descriptionInputContainerEl.textContent = "";
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

export class ToggleDataAttributeAction extends BaseDonationAction {
    /**
     * @param {string} dataAttributeName - The data attribute to toggle (without "data-" prefix)
     * @param {Function} toggleFunction - Function to call when applying or cleaning
     */
    setup(dataAttributeName, toggleFunction) {
        this.dataAttributeName = dataAttributeName;
        this.toggleFunction = toggleFunction;
    }

    /**
     * Determine if the data attribute is applied.
     *
     * @param {Object} context
     * @param {HTMLElement} context.editingElement
     * @returns {boolean}
     */
    isApplied({ editingElement }) {
        return !!editingElement.dataset[this.dataAttributeName];
    }

    /**
     * Apply the data attribute and call the toggle function.
     *
     * @param {Object} context
     * @param {HTMLElement} context.editingElement
     * @param {...*} restArgs - Extra args for toggleFunction
     */
    apply(context, ...restArgs) {
        const { editingElement } = context;
        editingElement.dataset[this.dataAttributeName] = "true";
        this.toggleFunction({ ...context, value: true }, ...restArgs);
    }

    /**
     * Remove the data attribute and call the toggle function.
     *
     * @param {Object} context
     * @param {HTMLElement} context.editingElement
     * @param {...*} restArgs - Extra args for toggleFunction
     */
    clean(context, ...restArgs) {
        const { editingElement } = context;
        delete editingElement.dataset[this.dataAttributeName];
        this.toggleFunction({ ...context, value: false }, ...restArgs);
    }
}

export class ToggleDisplayOptionsAction extends ToggleDataAttributeAction {
    static id = "toggleDisplayOptions";

    setup() {
        super.setup("displayOptions", this.toggleDisplayOptions);
    }

    toggleDisplayOptions({ editingElement, value }) {
        if (!value && editingElement.dataset.customAmount === "slider") {
            editingElement.dataset.customAmount = "freeAmount";
        } else if (value && !editingElement.dataset.prefilledOptions) {
            editingElement.dataset.customAmount = "slider";
        }
        this.rebuildPrefilledOptions(editingElement);
    }
}

export class TogglePrefilledOptionsAction extends ToggleDataAttributeAction {
    static id = "togglePrefilledOptions";

    setup() {
        super.setup("prefilledOptions", this.togglePrefilledOptions);
    }

    togglePrefilledOptions({ editingElement, value }) {
        if (!value && editingElement.dataset.displayOptions) {
            editingElement.dataset.customAmount = "slider";
        }
        this.rebuildPrefilledOptions(editingElement);
    }
}

export class ToggleDescriptionsAction extends ToggleDataAttributeAction {
    static id = "toggleDescriptions";

    setup() {
        super.setup("descriptions", ({ editingElement }) => {
            this.rebuildPrefilledOptions(editingElement);
        });
    }
}

export class SetPrefilledOptionsAction extends BaseDonationAction {
    static id = "setPrefilledOptions";

    getValue(context) {
        return this.getPrefilledOptionsList(context);
    }

    apply({ editingElement, value }) {
        // TODO AGAU: remove when merging https://github.com/odoo-dev/odoo/pull/4240
        {
            const options = JSON.parse(value);
            const amounts = options.map((option) => option.value);
            editingElement.dataset.donationAmounts = JSON.stringify(amounts);
        }

        editingElement.dataset.prefilledOptionsList = value;
        this.rebuildPrefilledOptions(editingElement, value);
    }
}

export class SelectAmountInputAction extends BaseDonationAction {
    static id = "selectAmountInput";

    isApplied({ editingElement, params }) {
        return editingElement.dataset.customAmount === params.mainParam;
    }

    apply({ editingElement, params }) {
        editingElement.dataset.customAmount = params.mainParam;
        this.rebuildPrefilledOptions(editingElement);
    }
}

export class SetMinimumAmountAction extends BuilderAction {
    static id = "setMinimumAmount";

    getValue({ editingElement }) {
        return editingElement.dataset.minimumAmount;
    }

    apply({ editingElement, value }) {
        editingElement.dataset.minimumAmount = value;
        const rangeSliderEl = editingElement.querySelector("#s_donation_range_slider");
        const amountInputEl = editingElement.querySelector("#s_donation_amount_input");
        if (rangeSliderEl) {
            rangeSliderEl.min = value;
        } else if (amountInputEl) {
            amountInputEl.min = value;
        }
    }
}

export class SetMaximumAmountAction extends BuilderAction {
    static id = "setMaximumAmount";

    getValue({ editingElement }) {
        return editingElement.dataset.maximumAmount;
    }

    apply({ editingElement, value }) {
        editingElement.dataset.maximumAmount = value;
        const rangeSliderEl = editingElement.querySelector("#s_donation_range_slider");
        const amountInputEl = editingElement.querySelector("#s_donation_amount_input");
        if (rangeSliderEl) {
            rangeSliderEl.max = value;
        } else if (amountInputEl) {
            amountInputEl.max = value;
        }
    }
}

export class SetSliderStepAction extends BuilderAction {
    static id = "setSliderStep";

    getValue({ editingElement }) {
        return editingElement.dataset.sliderStep;
    }

    apply({ editingElement, value }) {
        editingElement.dataset.sliderStep = value;
        const rangeSliderEl = editingElement.querySelector("#s_donation_range_slider");
        if (rangeSliderEl) {
            rangeSliderEl.step = value;
        }
    }
}

registry.category("website-plugins").add(DonationOptionPlugin.id, DonationOptionPlugin);
