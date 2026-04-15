import { useState } from "@odoo/owl";

import { Pager } from "@web/core/pager/pager";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

const pagerPatch = {
    setup() {
        super.setup();
        if (this.env.services["mail.store"]) {
            this.mailStore = useState(useService("mail.store"));
        }
    },
    get isDisabled() {
        return super.isDisabled || this.mailStore?.isChatterUploading;
    },
};
patch(Pager.prototype, pagerPatch);
