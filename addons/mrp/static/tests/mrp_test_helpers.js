import { mailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels } from "@web/../tests/web_test_helpers";
import { ResFake } from "@mrp/../tests/mock_server/mock_models/res_fake";

export function defineMrpModels() {
    return defineModels(mrpModels);
}

export const mrpModels = {
    ...mailModels,
    ResFake,
};
