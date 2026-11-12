import { mailModels } from "@mail/../tests/mail_test_helpers";
import { ResPartner } from "@phone_validation/../tests/mock_server/mock_models/res_partner";
import { defineModels } from "@web/../tests/web_test_helpers";

export const phoneValidationModels = { ...mailModels, ResPartner };

export function definePhoneValidationModels() {
    return defineModels(phoneValidationModels);
}
