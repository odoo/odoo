import { ResPartnerBank } from "./mock_server/mock_models/res_partner_bank";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

export const accountNumberModels = {
    ResPartnerBank,
};

export function defineAccountNumberModels() {
    return defineModels({ ...mailModels, ...accountNumberModels });
}
