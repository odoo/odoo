import { usePlugin } from "@odoo/owl";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { renderToElement } from "@web/core/utils/render";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

export class CoursePrerequisite extends Interaction {
    static selector = ".o_wslides_js_prerequisite_course";

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
    }

    start() {
        this.bootstrap.getOrCreateInstance(window.Popover, this.el, {
            trigger: "focus",
            placement: "bottom",
            container: "body",
            html: true,
            content: renderToElement("slide.course.prerequisite", {
                channels: JSON.parse(this.el.dataset.channels),
            }),
        });
    }
}

registry
    .category("public.interactions")
    .add("website_slides.course_prerequisite", CoursePrerequisite);
