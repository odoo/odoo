/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('custom_content_kanban_like_tour', {
    steps: () => [
        {
            trigger: "ul.nav a:contains(Quote Builder)",
            run: "click",
        },
        {
            trigger: "label:contains(Header)",
            run: "click",
        },
        {
            trigger: "h5:contains(custom_1) ~ div textarea",
            break: true,
            run: "edit Test",
        },
        ...stepUtils.saveForm(),
        // TODO VCR: Finish this
    ]
});
