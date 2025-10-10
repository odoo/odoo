import { CrmLead } from "@mail/core/common/model_definitions";
import { fields } from "@mail/core/common/record";

import { router } from "@web/core/browser/router";
import { patch } from "@web/core/utils/patch";

function setup() {
    this.href = fields.Attr("", {
        compute() {
            return router.stateToUrl({ model: "crm.lead", resId: this.id });
        },
    });
}
patch(CrmLead.prototype, {
    setup() {
        super.setup(...arguments);
        setup.call(this);
    },
});
