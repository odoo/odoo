import { fields, patchModel } from "@mail/model/export";

import { WebsiteVisitor } from "@website/mail/core/common/website_visitor_model";

export const websiteVisitorPatch = patchModel(WebsiteVisitor, {
    setup() {
        super.setup();
        this.discuss_channel_ids = fields.Many("discuss.channel");
        this.last_track_ids = fields.Many("website.track");
    },
});
