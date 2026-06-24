import { PortalChatterService } from "@portal/chatter/frontend/portal_chatter_service";

import { patch } from '@web/core/utils/patch';

patch(PortalChatterService.prototype, {
    get_props_from_el(chatterEl) {
        const props = super.get_props_from_el(...arguments);
        return {
            ...props,
            websiteId: chatterEl.getAttribute("data-website_id"),
        };
    },
});
