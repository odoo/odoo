import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { defineModels, fields, models } from "@web/../tests/web_test_helpers";

export class LunchProduct extends models.Model {
    _name = "lunch.product";

    name = fields.Char();
    is_favorite = fields.Boolean();
}

export function defineLunchProduct() {
    defineMailModels();
    defineModels(lunchModels);
}

export const lunchModels = {
    LunchProduct,
};
