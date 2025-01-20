import { ResPartnerBank } from "./mock_server/mock_models/res_partner_bank";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, mockEmojiLoading } from "@web/../tests/web_test_helpers";

export const baseIbanModels = {
    ResPartnerBank,
};

export function defineBaseIbanModels() {
    mockEmojiLoading();
    return defineModels({ ...mailModels, ...baseIbanModels });
}
