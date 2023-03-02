/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Record } from "@web/views/relational_model";

patch(Record.prototype, "mail.Record", {
    _getWidgetFromDefinition(definition) {
        if (definition.comodel !== "res.users") {
            return this._super(...arguments);
        }
        return definition.type === "many2one" ? "many2one_avatar_user" : "many2many_avatar_user";
    },
});
