/* @odoo-module */

import { imStatusService } from "@bus/im_status_service";
import { patch } from "@web/core/utils/patch";

export const imStatusServicePatchExtended = {
    dependencies: [...imStatusService.dependencies, "mail.store"],

    start(env, services) {
        super.start(env, services);
    },

    _handleImStatusUpdate(persona, im_status) {
        if (im_status == "online" && persona.out_of_office_date_end) {
            persona.im_status = "leave_online";
        } else if (im_status == "offline" && persona.out_of_office_date_end) {
            persona.im_status = "leave_offline";
        } else if (im_status == "away" && persona.out_of_office_date_end) {
            persona.im_status = "leave_away";
        } else {
            persona.im_status = im_status;
        }
    },
};
export const unpatchedImStatusService = patch(imStatusService, imStatusServicePatchExtended);
