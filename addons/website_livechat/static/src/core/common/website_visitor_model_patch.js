import { fields } from "@mail/model/export";

import { patch } from "@web/core/utils/patch";

import { WebsiteVisitor } from "@website/mail/core/common/website_visitor_model";

/** @type {import("models").WebsiteVisitor} */
const websiteVisitorPatch = {
    setup() {
        super.setup();
        this.last_track_ids = fields.Many("website.track");
    },
};
patch(WebsiteVisitor.prototype, websiteVisitorPatch);
