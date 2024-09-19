/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { parseDate } from '@web/core/l10n/dates';

publicWidget.registry.ProjectRatingImage = publicWidget.Widget.extend({
    selector: '.o_portal_project_rating .o_rating_image',

    /**
     * @override
     */
    start: function () {
        const el = this.el;
        Popover.getOrCreateInstance(el, {
            placement: "bottom",
            trigger: "hover",
            html: true,
            content: function () {
                const id = el.dataset.id;
                const ratingDateEl = el.dataset.ratingDate;
                const baseDate = parseDate(ratingDateEl);
                const duration = baseDate.toRelative();
                const ratingEl = document.querySelector(`#rating_${id}`);
                ratingEl.querySelector(".rating_timeduration").textContent = duration;
                return ratingEl.innerHTML;
            },
        });
        return this._super.apply(this, arguments);
    },
});
