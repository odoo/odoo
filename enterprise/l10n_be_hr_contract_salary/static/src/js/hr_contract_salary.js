/** @odoo-module **/

import hrContractSalary from "@hr_contract_salary/js/hr_contract_salary";
import { renderToElement } from "@web/core/utils/render";

hrContractSalary.include({
    events: Object.assign({}, hrContractSalary.prototype.events, {
        "change input[name='has_hospital_insurance_radio']": "onchangeHospital",
        "change input[name='insured_relative_children_manual']": "onchangeHospital",
        "change input[name='insured_relative_adults_manual']": "onchangeHospital",
        "change input[name='fold_insured_relative_spouse']": "onchangeHospital",
        "change input[name='fold_company_car_total_depreciated_cost']": "onchangeCompanyCar",
        "change input[name='fold_private_car_reimbursed_amount']": "onchangePrivateCar",
        "change input[name='fold_l10n_be_bicyle_cost']": "onchangePrivateBike",
        "change input[name='l10n_be_bicyle_cost_manual']": "onchangePrivateBike",
        "change input[name='l10n_be_has_ambulatory_insurance_radio']": "onchangeAmbulatory",
        "change input[name='l10n_be_ambulatory_insured_children_manual']": "onchangeAmbulatory",
        "change input[name='l10n_be_ambulatory_insured_adults_manual']": "onchangeAmbulatory",
        "change input[name='fold_l10n_be_ambulatory_insured_spouse']": "onchangeAmbulatory",
        "change input[name='children']": "onchangeChildren",
        "change input[name='fold_wishlist_car_total_depreciated_cost']": "onchangeWishlistCar",
    }),

    setUpBenefits() {
        this._super.apply(this, arguments);
        const fuelCardSlider = $("input[name='fuel_card_slider']");
        if (fuelCardSlider.length > 0) {
            const mandatoryBenefits = fuelCardSlider.data('benefit_ids-mandatory');
            if (mandatoryBenefits) {
                const anyMandatorySelected = mandatoryBenefits.trim().split(' ').some(adv => this.checkInputSelected(adv));

                if (!anyMandatorySelected) {
                    fuelCardSlider.attr("disabled", "disabled");
                    fuelCardSlider.parent().addClass('o_disabled');
                }
            }
        }
    },

    getBenefits() {
        var res = this._super.apply(this, arguments);
        res.contract.l10n_be_canteen_cost = parseFloat(
            this.el.querySelector("input[name='l10n_be_canteen_cost']").value || "0.0"
        );
        return res
    },

    updateGrossToNetModal(data) {
        this._super(data);
        const dblHolidayWageEl = this.el.querySelector("input[name='double_holiday_wage']");
        if (dblHolidayWageEl) {
            dblHolidayWageEl.value = data["double_holiday_wage"];
        }
        if (data["wishlist_simulation"]) {
            const modal_body = renderToElement('hr_contract_salary.salary_package_resume', {
                'lines': data.wishlist_simulation.resume_lines_mapped,
                'categories': data.wishlist_simulation.resume_categories,
                'configurator_warning': data.wishlist_warning,
                'hide_details': true,
            });
            const wishlistModalEl = this.el.querySelector('main[name="wishlist_modal_body"]');
            wishlistModalEl.innerHTML = "";
            wishlistModalEl.appendChild(modal_body);
        }
        const $submit_button = $("button#hr_cs_submit");
        if ($submit_button.length) {
            $submit_button.prop('disabled', !!data["configurator_warning"]);
        }
    },

    onchangeCompanyCar: function(event) {
        const privateCarInputEl = this.el.querySelector(
            "input[name='fold_private_car_reimbursed_amount']"
        );
        if (event.target.checked && privateCarInputEl && privateCarInputEl.checked) {
            privateCarInputEl.click();
        }
    },

    onchangePrivateCar: function(event) {
        const companyCarInputEl = this.el.querySelector(
            "input[name='fold_company_car_total_depreciated_cost']"
        );
        if (event.target.checked && companyCarInputEl && companyCarInputEl.checked) {
            companyCarInputEl.click();
        }
    },

    onchangeWishlistCar: function(event) {
        if (event.target.checked) {
            const anchorEl = document.createElement("a");
            anchorEl.classList.add("btn", "btn-link", "ps-0", "pt-0", "pb-2", "m-3");
            anchorEl.setAttribute("role", "button");
            anchorEl.dataset.bsToggle = "modal";
            anchorEl.dataset.bsTarget = "#hr_cs_modal_wishlist";
            anchorEl.dataset.bsBackdrop = "false";
            anchorEl.dataset.bsDismiss = "modal";
            anchorEl.setAttribute("name", "wishlist_simulation_button");
            anchorEl.textContent = "Simulation";
            const nextToSelectEl = this.el.querySelector(
                'input[name="wishlist_car_total_depreciated_cost"]'
            ).parentElement;
            nextToSelectEl.parentNode.insertBefore(
                anchorEl,
                nextToSelectEl.nextSibling
            );
        } else {
            const wishlistSimulationButtonEl = this.el.querySelector(
                'a[name="wishlist_simulation_button"]'
            );
            if (wishlistSimulationButtonEl) {
                wishlistSimulationButtonEl.remove();
            }
        }
    },

    onchangePrivateBike: function() {
        const privateBikeCheckboxEl = this.el.querySelector("input[name='fold_l10n_be_bicyle_cost']");
        const privateBikeInputEl = this.el.querySelector("input[name='l10n_be_bicyle_cost_manual']");
        
        const isCheckboxChecked = privateBikeCheckboxEl?.checked || false;
        const privateBikeValue = parseFloat(privateBikeInputEl?.value || "0.0");
        
        if (isCheckboxChecked && privateBikeValue > 0) {
            // Set the fuel card values to 0 and disable it
            const fuelCardSliderEl = this.el.querySelector("input[name='fuel_card_slider']");
            const fuelCardEl = this.el.querySelector("input[name='fuel_card']");
            if (fuelCardSliderEl) {
                fuelCardSliderEl.value = 0;
            }
            if (fuelCardEl) {
                fuelCardEl.value = 0;
            }
            this.el.querySelector("label[for='fuel_card']")?.parentElement.classList.add("o_disabled");
        } else {
            // Enable the fuel card element when checkbox is unchecked or value is 0
            this.el.querySelector("label[for='fuel_card']")?.parentElement.classList.remove("o_disabled");
        }
    },

    onchangeFoldedResetInteger(benefitField) {
        if (benefitField === 'private_car_reimbursed_amount_manual' || benefitField === 'l10n_be_bicyle_cost_manual') {
            return false;
        } else {
            return this._super.apply(this, arguments);
        }
    },

    start: async function () {
        const res = await this._super(...arguments);
        this.onchangeChildren();
        this.onchangeHospital();
        // Hack to make these benefits required. TODO: remove when required benefits are supported.
        this.el
            .querySelector("textarea[name='l10n_be_hospital_insurance_notes_text']")
            ?.setAttribute("required", true);
        this.el
            .querySelector("textarea[name='l10n_be_ambulatory_insurance_notes_text']")
            ?.setAttribute("required", true);

        this.el
            .querySelector("input[name='insured_relative_children']")
            ?.parentElement.classList.add("d-none");
        this.el
            .querySelector("input[name='insured_relative_adults']")
            ?.parentElement.classList.add("d-none");
        this.el
            .querySelector("input[name='insured_relative_spouse']")
            ?.parentElement.classList.add("d-none");
        this.el
            .querySelector("input[name='l10n_be_hospital_insurance_notes']")
            ?.parentElement.classList.add("d-none");
        const childrenEl = this.el.querySelector("input[name='insured_relative_children_manual']");
        const childrenStrongEl = document.createElement("strong");
        childrenStrongEl.classList.add("mt8");
        childrenStrongEl.textContent = "# Children < 19";
        childrenEl?.parentNode.insertBefore(childrenStrongEl, childrenEl);

        const adultsEl = this.el.querySelector("input[name='insured_relative_adults_manual']");
        const adultStrongEl = document.createElement("strong");
        adultStrongEl.classList.add("mt8");
        adultStrongEl.textContent = "# Children >= 19";
        adultsEl?.parentNode.insertBefore(adultStrongEl, adultsEl);

        const insuranceEl = this.el.querySelector(
            "textarea[name='l10n_be_hospital_insurance_notes_text']"
        );
        const insuranceNoteStrongEl = document.createElement("strong");
        insuranceNoteStrongEl.classList.add("mt8");
        insuranceNoteStrongEl.textContent = "Additional Information";
        insuranceEl?.parentNode.insertBefore(insuranceNoteStrongEl, insuranceEl);
        this.onchangeAmbulatory();
        this.el
            .querySelector("input[name='l10n_be_ambulatory_insured_children']")
            ?.parentElement.classList.add("d-none");
        this.el
            .querySelector("input[name='l10n_be_ambulatory_insured_adults']")
            ?.parentElement.classList.add("d-none");
        this.el
            .querySelector("input[name='l10n_be_ambulatory_insured_spouse']")
            ?.parentElement.classList.add("d-none");
        this.el
            .querySelector("input[name='l10n_be_ambulatory_insurance_notes']")
            ?.parentElement.classList.add("d-none");
        const ambulatoryChildrenEl = this.el.querySelector(
            "input[name='l10n_be_ambulatory_insured_children_manual']"
        );
        ambulatoryChildrenEl?.parentNode.insertBefore(
            childrenStrongEl.cloneNode(true), ambulatoryChildrenEl
        );

        const ambulatoryAdultEl = this.el.querySelector(
            "input[name='l10n_be_ambulatory_insured_adults_manual']"
        );
        ambulatoryAdultEl?.parentNode.insertBefore(
            adultStrongEl.cloneNode(true), ambulatoryAdultEl
        );

        const ambulatoryInsuranceEl = this.el.querySelector(
            "textarea[name='l10n_be_ambulatory_insurance_notes_text']"
        );
        ambulatoryInsuranceEl?.parentNode.insertBefore(
            insuranceNoteStrongEl.cloneNode(true), ambulatoryInsuranceEl
        );
        return res;
    },

    onchangeHospital: function() {
        const insranceRadioEls = this.el.querySelectorAll(
            "input[name='has_hospital_insurance_radio']"
        );
        const hasInsurance = insranceRadioEls[insranceRadioEls.length - 1]?.checked;
        if (hasInsurance) {
            // Show fields
            this.el
                .querySelector("label[for='insured_relative_children']")
                .parentElement.classList.remove("d-none");
            this.el
                .querySelector("label[for='insured_relative_adults']")
                .parentElement.classList.remove("d-none");
            this.el
                .querySelector("label[for='insured_relative_spouse']")
                .parentElement.classList.remove("d-none");
            this.el
                .querySelector("label[for='l10n_be_hospital_insurance_notes']")
                .parentElement.classList.remove("d-none");
            // Only show notes when either an extra spouse or children are insured.
            const insuredSpouse = this.el
                .querySelector("input[name='fold_insured_relative_spouse']")
                ?.checked;
            const insuredRelativeChildren =
                parseInt(
                    this.el.querySelector("input[name='insured_relative_children_manual']").value
                ) > 0;
            const insuredRelativeAdults =
                parseInt(
                    this.el.querySelector("input[name='insured_relative_adults_manual']").value
                ) > 0;
            if (insuredSpouse || insuredRelativeChildren || insuredRelativeAdults ) {
                this.el
                    .querySelector("label[for='l10n_be_hospital_insurance_notes']")
                    .parentElement.classList.remove("d-none");
            }
            else {
                this.el
                    .querySelector("label[for='l10n_be_hospital_insurance_notes']")
                    .parentElement.classList.add("d-none");
            }
        } else {
            // Reset values
            this.el.querySelector("input[name='fold_insured_relative_spouse']")?.removeAttribute('checked');
            const relativeChildrenEl = this.el
                .querySelector("input[name='insured_relative_children_manual']");
            const relativeAdultsEl = this.el
                .querySelector("input[name='insured_relative_adults_manual']");
            if (relativeChildrenEl) {
                relativeChildrenEl.value = 0;
            }
            if (relativeAdultsEl) {
                relativeAdultsEl.value = 0;
            }
            // Hide fields
            this.el
                .querySelector("label[for='insured_relative_children']")
                ?.parentElement.classList.add("d-none");
            this.el
                .querySelector("label[for='insured_relative_adults']")
                ?.parentElement.classList.add("d-none");
            this.el
                .querySelector("label[for='insured_relative_spouse']")
                ?.parentElement.classList.add("d-none");
            this.el
                .querySelector("label[for='l10n_be_hospital_insurance_notes']")
                ?.parentElement.classList.add("d-none");
        }
    },

    onchangeAmbulatory: function() {
        const insuranceRadiosEls = this.el.querySelectorAll(
            "input[name='l10n_be_has_ambulatory_insurance_radio']"
        );
        const hasInsurance = insuranceRadiosEls[insuranceRadiosEls.length - 1]?.checked;
        if (hasInsurance) {
            // Show fields
            this.el
                .querySelector("label[for='l10n_be_ambulatory_insured_children']")
                .parentElement.classList.remove("d-none");
            this.el
                .querySelector("label[for='l10n_be_ambulatory_insured_adults']")
                .parentElement.classList.remove("d-none");
            this.el
                .querySelector("label[for='l10n_be_ambulatory_insured_spouse']")
                .parentElement.classList.remove("d-none");
            this.el
                .querySelector("label[for='l10n_be_ambulatory_insurance_notes']")
                .parentElement.classList.remove("d-none");
            // Only show notes when either an extra spouse or children are insured.
            const insuredSpouse = this.el
                .querySelector("input[name='fold_l10n_be_ambulatory_insured_spouse']")
                ?.checked;
            const insuredRelativeChildren =
                parseInt(
                    this.el.querySelector(
                        "input[name='l10n_be_ambulatory_insured_children_manual']"
                    ).value
                ) > 0;
            const insuredRelativeAdults =
                parseInt(
                    this.el.querySelector("input[name='l10n_be_ambulatory_insured_adults_manual']")
                        .value
                ) > 0;
            if (insuredSpouse || insuredRelativeChildren || insuredRelativeAdults ) {
                this.el
                    .querySelector("label[for='l10n_be_ambulatory_insurance_notes']")
                    .parentElement.classList.remove("d-none");
            } else {
                this.el
                    .querySelector("label[for='l10n_be_ambulatory_insurance_notes']")
                    .parentElement.classList.add("d-none");
            }
        } else {
            // Reset values
            this.el.querySelector(
                "input[name='fold_l10n_be_ambulatory_insured_spouse']"
            )?.removeAttribute('checked')
            const ambulatoryChildrenEl = this.el
                .querySelector("input[name='l10n_be_ambulatory_insured_children_manual']");
            const ambulatoryAdultsEl = this.el
                .querySelector("input[name='l10n_be_ambulatory_insured_adults_manual']");
            if (ambulatoryChildrenEl) {
                ambulatoryChildrenEl.value = 0;
            }
            if (ambulatoryAdultsEl) {
                ambulatoryAdultsEl.value = 0;
            }
            // Hide fields
            this.el
                .querySelector("label[for='l10n_be_ambulatory_insured_children']")
                ?.parentElement.classList.add("d-none");
            this.el
                .querySelector("label[for='l10n_be_ambulatory_insured_adults']")
                ?.parentElement.classList.add("d-none");
            this.el
                .querySelector("label[for='l10n_be_ambulatory_insured_spouse']")
                ?.parentElement.classList.add("d-none");
            this.el
                .querySelector("label[for='l10n_be_ambulatory_insurance_notes']")
                ?.parentElement.classList.add("d-none");
        }
    },

    onchangeChildren(event) {
        const disabledChildrenEl = this.el.querySelector("input[name='disabled_children_bool']");
        const disabledChildrenNumberEl = this.el.querySelector(
            "input[name='disabled_children_number']"
        );
        const childCount = parseInt(event && event.currentTarget && event.currentTarget.value);

        if (isNaN(childCount) || childCount === 0) {
            if (disabledChildrenNumberEl) {
                disabledChildrenNumberEl.value = 0;
            }

            if (disabledChildrenEl?.checked) {
                disabledChildrenEl.click();
            }
            disabledChildrenEl?.parentElement.classList.add("d-none");
        } else {
            disabledChildrenEl?.parentElement.classList.remove("d-none");
        }
    },
});
