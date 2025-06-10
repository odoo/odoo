import { patch } from "@web/core/utils/patch";
import { Composer } from "../common/composer_model";
import { markup } from "@odoo/owl";
import { fields } from "@mail/core/common/record";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.body = fields.Html("<p><br></p>");
    },
    clear() {
        super.clear();
        this.body = markup("<p><br></p>");
    },
});
