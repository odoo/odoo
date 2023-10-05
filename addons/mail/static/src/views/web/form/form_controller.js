/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { x2ManyCommands } from "@web/core/orm_service";

patch(FormController.prototype, {
    onWillLoadRoot(nextConfiguration) {
        super.onWillLoadRoot(...arguments);
        const isSameThread =
            this.model.root?.resId === nextConfiguration.resId &&
            this.model.root?.resModel === nextConfiguration.resModel;
        if (isSameThread) {
            // not first load
            const { resModel, resId } = this.model.root;
            this.env.bus.trigger("MAIL:RELOAD-THREAD", { model: resModel, id: resId });
        }
    },

    async onWillSaveRecord(record, changes) {
        if (record.resModel === "mail.compose.message") {
            const parser = new DOMParser();
            const htmlBody = parser.parseFromString(changes.body, "text/html");
            const partnerElements = htmlBody.querySelectorAll('[data-oe-model="res.partner"]');
            const partnerIds = Array.from(partnerElements).map((element) =>
                parseInt(element.dataset.oeId)
            );
            if (partnerIds.length) {
                if (changes.partner_ids[0] && changes.partner_ids[0][0] === x2ManyCommands.SET) {
                    partnerIds.push(...changes.partner_ids[0][2]);
                }
                changes.partner_ids = [x2ManyCommands.set(partnerIds)];
            }
        }
    },
});
