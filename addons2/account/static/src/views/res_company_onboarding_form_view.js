/** @odoo-module **/

import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";

import CompanyOnboardingFormController from "./res_company_onboarding_form_controller.js";


const CompanyOnboardingFormView = {
    ...formView,
    Controller: CompanyOnboardingFormController,
};


registry.category("views").add("company_onboarding_form", CompanyOnboardingFormView);
