/** @odoo-module **/

import hrContractSalary from "@hr_contract_salary/js/hr_contract_salary";

hrContractSalary.include({
    events: Object.assign({}, hrContractSalary.prototype.events, {
        "change input[name='has_hospital_insurance_radio']": "onchangeHospital",
        "change input[name='fold_company_car_total_depreciated_cost']": "onchangeCompanyCar",
        "change input[name='fold_private_car_reimbursed_amount']": "onchangePrivateCar",
        "change input[name='fold_l10n_be_bicyle_cost']": "onchangePrivateBike",
        "change input[name='l10n_be_has_ambulatory_insurance_radio']": "onchangeAmbulatory",
        "change input[name='children']": "onchangeChildren",
    }),

    getBenefits() {
        var res = this._super.apply(this, arguments);
        res.contract.l10n_be_canteen_cost = parseFloat($("input[name='l10n_be_canteen_cost']").val() || "0.0");
        return res
    },

    updateGrossToNetModal(data) {
        this._super(data);
        $("input[name='double_holiday_wage']").val(data['double_holiday_wage']);
    },

    onchangeCompanyCar: function(event) {
        var private_car_input = $("input[name='fold_private_car_reimbursed_amount']")
        if (event.target.checked && private_car_input.length && private_car_input[0].checked) {
            private_car_input.click()
        }
    },

    onchangePrivateCar: function(event) {
        var company_car_input = $("input[name='fold_company_car_total_depreciated_cost']")
        if (event.target.checked && company_car_input.length && company_car_input[0].checked) {
            company_car_input.click()
        }
    },

    onchangePrivateBike: function(event) {
        if (event.target.checked) {
            // Set the fuel card slider value to 0 and disable it
            $("input[name='fuel_card_slider']").val(0).prop('disabled', true);
            $("input[name='fuel_card']").val(0);
        } else {
            // Enable the fuel card slider when "Private Bike" is unchecked
            $("input[name='fuel_card_slider']").prop('disabled', false);
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
        $("input[name='insured_relative_children']").parent().addClass('d-none');
        $("input[name='insured_relative_adults']").parent().addClass('d-none');
        $("input[name='insured_relative_spouse']").parent().addClass('d-none');
        $("input[name='l10n_be_hospital_insurance_notes']").parent().addClass('d-none');
        $("input[name='insured_relative_children_manual']").before($('<strong>', {
            class: 'mt8',
            text: '# Children < 19'
        }));
        $("input[name='insured_relative_adults_manual']").before($('<strong>', {
            class: 'mt8',
            text: '# Children >= 19'
        }));
        $("textarea[name='l10n_be_hospital_insurance_notes_text']").before($('<strong>', {
            class: 'mt8',
            text: 'Additional Information'
        }));
        this.onchangeAmbulatory();
        $("input[name='l10n_be_ambulatory_insured_children']").parent().addClass('d-none');
        $("input[name='l10n_be_ambulatory_insured_adults']").parent().addClass('d-none');
        $("input[name='l10n_be_ambulatory_insured_spouse']").parent().addClass('d-none');
        $("input[name='l10n_be_ambulatory_insurance_notes']").parent().addClass('d-none');
        $("input[name='l10n_be_ambulatory_insured_children_manual']").before($('<strong>', {
            class: 'mt8',
            text: '# Children < 19'
        }));
        $("input[name='l10n_be_ambulatory_insured_adults_manual']").before($('<strong>', {
            class: 'mt8',
            text: '# Children >= 19'
        }));
        $("textarea[name='l10n_be_ambulatory_insurance_notes_text']").before($('<strong>', {
            class: 'mt8',
            text: 'Additional Information'
        }));
        return res;
    },

    onchangeHospital: function() {
        const hasInsurance = $("input[name='has_hospital_insurance_radio']:last").prop('checked');
        if (hasInsurance) {
            // Show fields
            $("label[for='insured_relative_children']").parent().removeClass('d-none');
            $("label[for='insured_relative_adults']").parent().removeClass('d-none');
            $("label[for='insured_relative_spouse']").parent().removeClass('d-none');
            $("label[for='l10n_be_hospital_insurance_notes']").parent().removeClass('d-none');
        } else {
            // Reset values
            $("input[name='fold_insured_relative_spouse']").prop('checked', false);
            $("input[name='insured_relative_children_manual']").val(0);
            $("input[name='insured_relative_adults_manual']").val(0);
            // Hide fields
            $("label[for='insured_relative_children']").parent().addClass('d-none');
            $("label[for='insured_relative_adults']").parent().addClass('d-none');
            $("label[for='insured_relative_spouse']").parent().addClass('d-none');
            $("label[for='l10n_be_hospital_insurance_notes']").parent().addClass('d-none');
        }
    },

    onchangeAmbulatory: function() {
        const hasInsurance = $("input[name='l10n_be_has_ambulatory_insurance_radio']:last").prop('checked');
        if (hasInsurance) {
            // Show fields
            $("label[for='l10n_be_ambulatory_insured_children']").parent().removeClass('d-none');
            $("label[for='l10n_be_ambulatory_insured_adults']").parent().removeClass('d-none');
            $("label[for='l10n_be_ambulatory_insured_spouse']").parent().removeClass('d-none');
            $("label[for='l10n_be_ambulatory_insurance_notes']").parent().removeClass('d-none');
        } else {
            // Reset values
            $("input[name='fold_l10n_be_ambulatory_insured_spouse']").prop('checked', false);
            $("input[name='l10n_be_ambulatory_insured_children_manual']").val(0);
            $("input[name='l10n_be_ambulatory_insured_adults_manual']").val(0);
            // Hide fields
            $("label[for='l10n_be_ambulatory_insured_children']").parent().addClass('d-none');
            $("label[for='l10n_be_ambulatory_insured_adults']").parent().addClass('d-none');
            $("label[for='l10n_be_ambulatory_insured_spouse']").parent().addClass('d-none');
            $("label[for='l10n_be_ambulatory_insurance_notes']").parent().addClass('d-none');
        }
    },

    onchangeChildren() {
        const disabledChildren = $("input[name='disabled_children_bool']");
        const disabledChildrenNumber = $("input[name='disabled_children_number']");
        const childrenInput = $("input[name='children']", this.el)
        const childCount = parseInt(childrenInput.length > 0 && childrenInput.val());

        if (isNaN(childCount) || childCount === 0) {
            disabledChildrenNumber.val(0);

            if (disabledChildren.prop('checked')) {
                disabledChildren.click();
            }
            disabledChildren.parent().addClass('d-none');
        } else {
            disabledChildren.parent().removeClass('d-none');
        }
    },
});
