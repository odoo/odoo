import { RatingComposer } from "@portal_rating/chatter/frontend/rating_composer";

import { patch } from "@web/core/utils/patch";
import { useEffect } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

patch(RatingComposer.prototype, {
    setup() {
        super.setup(...arguments);
        useEffect(
            () => {
                const reviewEl = document.querySelector("#review-tab");
                if (reviewEl && this.props.thread.rating_count) {
                    reviewEl.textContent = _t("Reviews (%s)", this.props.thread.rating_count);
                    
                }
            },
            () => [this.props.thread.rating_count]
        );
    },
});
