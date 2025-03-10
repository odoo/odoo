import { RatingComposer } from "@portal_rating/chatter/frontend/rating_composer";

import { useEffect } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { renderToElement } from "@web/core/utils/render";

const ratingComposerPatch = {
    setup() {
        super.setup(...arguments);
        useEffect(
            (ratingCount, ratingAvg) => {
                const reviewEl = document.querySelector("#review-tab");
                if (reviewEl) {
                    reviewEl.textContent = ratingCount
                        ? _t("Reviews (%s)", ratingCount)
                        : _t("Reviews");
                }
                const starsEl = document.querySelector(".o_rating_popup_composer_stars");
                if (starsEl) {
                    const stars = renderToElement("portal_rating.rating_stars_static", {
                        inline_mode: true,
                        val: ratingAvg || 0,
                    });
                    starsEl.replaceChildren(stars);
                }
            },
            () => [this.props.thread.rating_count, this.props.thread.rating_avg]
        );
    },
};
patch(RatingComposer.prototype, ratingComposerPatch);
