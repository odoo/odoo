// Part of Odoo. See LICENSE file for full copyright and licensing details.
import { MockPosData } from "@point_of_sale/../tests/unit/pos_app_tests";
import { patch } from "@web/core/utils/patch";

patch(MockPosData.prototype, {
    get data() {
        const data = super.data;
        data.models["event.event"] = { relations: {}, fields: {}, data: [] };
        data.models["event.event.ticket"] = { relations: {}, fields: {}, data: [] };
        data.models["event.registration"] = { relations: {}, fields: {}, data: [] };
        data.models["event.registration.answer"] = { relations: {}, fields: {}, data: [] };
        data.models["event.question"] = { relations: {}, fields: {}, data: [] };
        return data;
    },
});
