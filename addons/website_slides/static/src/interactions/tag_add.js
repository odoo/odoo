import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { CourseTagAddDialog } from "@website_slides/js/public/components/course_tag_add_dialog/course_tag_add_dialog";

export class TagAdd extends Interaction {
    static selector = ".o_wslides_js_channel_tag_add";
    dynamicContent = {
        _root: {
            "t-on-click.prevent": this.onClick,
        },
    };

    onClick() {
        const data = this.el.dataset;
        this.services.dialog.add(CourseTagAddDialog, {
            channelId: parseInt(data.channelId, 10),
            tagIds: data.channelTagIds ? JSON.parse(data.channelTagIds) : [],
        });
    }
}

registry
    .category("public.interactions")
    .add("website_slides.tag_add", TagAdd);
