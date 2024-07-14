/** @odoo-module **/

import { TagsList } from "@web/core/tags_list/tags_list";


export class HelpdeskSLATagsList extends TagsList {

    getSLAStatusIcon(tag) {
        let iconType = "";
        if (tag.slaStatus === "failed") {
            iconType = "times";
        } else if (tag.slaStatus === "reached") {
            iconType = "check";
        }
        return iconType ? `fa fa-${iconType}-circle me-2`: "";
    }

}

HelpdeskSLATagsList.template = "helpdesk.SLATagsList";
