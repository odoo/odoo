import { Chatter } from "@mail/chatter/web_portal/chatter";

import { patch } from "@web/core/utils/patch";
import { useSubEnv } from "@odoo/owl";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        useSubEnv({
            projectSharingId: this.props.projectSharingId,
        });
    },
});
Chatter.props = [...Chatter.props, "token?", "projectSharingId?"];
