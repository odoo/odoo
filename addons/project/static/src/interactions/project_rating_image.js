import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { parseDate } from '@web/core/l10n/dates';

export class ProjectRatingImage extends Interaction {
    static selector = ".o_portal_project_rating .o_rating_image";

    start() {
        window.Popover.getOrCreateInstance(this.el, {
            placement: "bottom",
            trigger: "hover",
            html: true,
            content: () => {
                const duration = parseDate(this.el.dataset.ratingDate).toRelative();
                const ratingEl = document.querySelector('#rating_' + this.el.dataset.id);
                ratingEl.querySelector(".rating_timeduration").textContent = duration;
                return ratingEl.outerHTML;
            },
        });
    }
}

registry
    .category("public.interactions")
    .add("project.project_rating_image", ProjectRatingImage);
