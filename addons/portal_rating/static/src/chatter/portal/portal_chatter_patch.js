import { PortalChatter } from "@portal/chatter/portal/portal_chatter";
import { PortalRatingPlugin } from "@portal_rating/chatter/portal/portal_rating_plugin";

import { patch } from "@web/core/utils/patch";
import { providePlugins, t, usePlugin, useProps } from "@odoo/owl";

patch(PortalChatter.prototype, {
    setup() {
        super.setup(...arguments);
        providePlugins([PortalRatingPlugin]);

        this.portalChatterProps = useProps({
            reviewChatter: t.any().optional(),
        });
        usePlugin(PortalRatingPlugin).reviewChatter.set(this.portalChatterProps.reviewChatter ?? false);
    },
});
