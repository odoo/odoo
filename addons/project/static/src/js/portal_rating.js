/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { parseDate } from '@web/core/l10n/dates';

publicWidget.registry.ProjectRatingImage = publicWidget.Widget.extend({
    selector: '.o_portal_project_rating .o_rating_image',

    /**
     * @override
     */
    start: function () {
        Popover.getOrCreateInstace(this.el, {
            placement: 'bottom',
            trigger: 'hover',
            html: true,
            content: function (elem) {
                const id = elem.getAttribute("data-id");
                const ratingDate = elem.getAttribute("data-rating-date");
                var baseDate = parseDate(ratingDate);
                var duration = baseDate.toRelative();
                const ratingEL = document.querySelector("#rating_" + id);
                ratingEL.querySelector(".rating_timeduration").textContent = duration;
                return ratingEL.innerHTML;
            },
        });
        return this._super.apply(this, arguments);
    },
});
