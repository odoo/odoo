/** @odoo-module native */
import { ResPartnerBankAccount } from "./mock_server/mock_models/res_partner_bank_account.js";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";

export const accountIbanModels = {
    ResPartnerBankAccount,
};

export function defineAccountIbanModels() {
    return defineModels({ ...mailModels, ...accountIbanModels });
}
