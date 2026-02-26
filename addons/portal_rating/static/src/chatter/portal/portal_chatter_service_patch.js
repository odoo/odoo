import { PortalChatterService } from "@portal/chatter/portal/portal_chatter_service";

import { patch } from "@web/core/utils/patch";

patch(PortalChatterService.prototype, {
    getProps(chatterEl) {
        const props = super.getProps(chatterEl);
        if (props.displayRating) {
            if (parseInt(chatterEl.getAttribute("data-allow_composer"))) {
                props.reviewChatter = true;
            }
        }
        return props;
    },
});
