import { PortalChatter } from "@portal/chatter/portal/portal_chatter";
import { PortalRatingPlugin } from "@portal_rating/chatter/portal/portal_rating_plugin";

import { patch } from "@web/core/utils/patch";
import { plugin, providePlugins } from "@odoo/owl";

patch(PortalChatter.prototype, {
    setup() {
        super.setup(...arguments);
        providePlugins([PortalRatingPlugin]);
        plugin(PortalRatingPlugin).reviewChatter.set(this.props.reviewChatter ?? false);
    },
});
