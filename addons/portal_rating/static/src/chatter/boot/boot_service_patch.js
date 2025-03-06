import { portalChatterBootService } from "@portal/chatter/boot/boot_service";

import { patch } from "@web/core/utils/patch";

const bootServicePatch = {
    get root() {
        return document.querySelector(".o_rating_popup_composer") || super.root;
    },
};
patch(portalChatterBootService, bootServicePatch);
