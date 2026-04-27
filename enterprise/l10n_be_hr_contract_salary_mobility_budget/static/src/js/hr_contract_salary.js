/** @odoo-module **/

import hrContractSalary from "@hr_contract_salary/js/hr_contract_salary";

hrContractSalary.include({
    events: Object.assign({}, hrContractSalary.prototype.events, {
        "change input[name='fold_l10n_be_mobility_budget_amount_monthly']": "onchangeMobility",
    }),

    start: async function () {
        const res = await this._super(...arguments);
        this.onchangeMobility();
        return res
    },

    updateGrossToNetModal(data) {
        this._super(data);
        $("input[name='l10n_be_mobility_budget_amount_monthly']").val(data['l10n_be_mobility_budget_amount_monthly']);
    },

    onchangeMobility: function(event) {
        const hasMobility = this.el.querySelector(`input[name='fold_l10n_be_mobility_budget_amount_monthly']`)?.checked;
        const transportRelatedFields = [
            "fold_company_car_total_depreciated_cost",
            "fold_private_car_reimbursed_amount",
            "fold_l10n_be_bicyle_cost",
            "fold_wishlist_car_total_depreciated_cost",
            "fold_l10n_be_bicyle_cost",
            "fold_wishlist_car_total_depreciated_cost",
            "fold_public_transport_reimbursed_amount",
            "fold_train_transport_reimbursed_amount",
            "fold_wishlist_car_total_depreciated_cost",
        ];
        if (hasMobility) {
            for (const fieldName of transportRelatedFields) {
                const element = this.el.querySelector(`input[name='${fieldName}']`);
                if (element && element.checked) {
                    element.click();
                }
            }

            const fuelCardSliderEl = this.el.querySelector("input[name='fuel_card_slider']");
            const fuelCardEl = this.el.querySelector("input[name='fuel_card']");
            if (fuelCardSliderEl) {
                fuelCardEl.value = 0;
                fuelCardEl.disabled = true;
            }
            if (fuelCardEl) {
                fuelCardEl.value = 0;
            }

            this.el.querySelector("label[for='company_car_total_depreciated_cost']")?.removeAttribute('checked');
            this.el.querySelector("label[for='company_car_total_depreciated_cost']")?.parentElement.classList.add("o_disabled");
            this.el.querySelector("label[for='wishlist_car_total_depreciated_cost']")?.parentElement.classList.add("o_disabled");
            this.el.querySelector("label[for='wishlist_car_total_depreciated_cost']")?.parentElement.classList.add("o_disabled");
            this.el.querySelector("label[for='public_transport_reimbursed_amount']")?.parentElement.classList.add("o_disabled");
            this.el.querySelector("label[for='train_transport_reimbursed_amount']")?.parentElement.classList.add("o_disabled");
            this.el.querySelector("label[for='private_car_reimbursed_amount']")?.parentElement.classList.add("o_disabled");
            this.el.querySelector("label[for='l10n_be_bicyle_cost']")?.parentElement.classList.add("o_disabled");
            this.el.querySelector("label[for='fuel_card']")?.parentElement.classList.add("o_disabled");
        } else {
            this.el.querySelector("label[for='company_car_total_depreciated_cost']")?.parentElement.classList.remove("o_disabled");
            this.el.querySelector("label[for='wishlist_car_total_depreciated_cost']")?.parentElement.classList.remove("o_disabled");
            this.el.querySelector("label[for='wishlist_car_total_depreciated_cost']")?.parentElement.classList.remove("o_disabled");
            this.el.querySelector("label[for='public_transport_reimbursed_amount']")?.parentElement.classList.remove("o_disabled");
            this.el.querySelector("label[for='train_transport_reimbursed_amount']")?.parentElement.classList.remove("o_disabled");
            this.el.querySelector("label[for='private_car_reimbursed_amount']")?.parentElement.classList.remove("o_disabled");
            this.el.querySelector("label[for='l10n_be_bicyle_cost']")?.parentElement.classList.remove("o_disabled");
            this.el.querySelector("label[for='fuel_card']")?.parentElement.classList.remove("o_disabled");
        }
    }
});
