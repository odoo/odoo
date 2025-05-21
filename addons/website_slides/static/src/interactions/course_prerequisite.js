import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { renderToElement } from "@web/core/utils/render";

export class CoursePrerequisite extends Interaction {
    static selector = ".o_wslides_js_prerequisite_course";

    assetBundles = ["website_slides.assets_widget_xml"];
    // xmlTemplates = ["/website_slides/static/src/xml/slide_course_prerequisite.xml"];

    start() {
        const bsPopover = window.Popover.getOrCreateInstance(this.el, {
            trigger: 'focus',
            placement: 'bottom',
            container: 'body',
            html: true,
            content: renderToElement('slide.course.prerequisite', {
                channels: JSON.parse(this.el.dataset.channels)
            }),
        });
        this.registerCleanup(() => bsPopover.dispose());
    }
}

registry
    .category("public.interactions")
    .add("website_slides.course_prerequisite", CoursePrerequisite);
