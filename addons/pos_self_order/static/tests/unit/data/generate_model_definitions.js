import { defineModels } from "@web/../tests/web_test_helpers";
import { mailModels } from "@mail/../tests/mail_test_helpers";
import { hootPosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PosSelfOrderCustomLink } from "./pos_self_order_custom_link.data";

export const hootPosSelfModels = [...hootPosModels, PosSelfOrderCustomLink];

export const definePosSelfModels = () => {
    const posModelNames = hootPosSelfModels.map(
        (modelClass) => modelClass.prototype.constructor._name
    );
    const modelsFromMail = Object.values(mailModels).filter(
        (modelClass) => !posModelNames.includes(modelClass.prototype.constructor._name)
    );
    defineModels([...modelsFromMail, ...hootPosSelfModels]);
};
