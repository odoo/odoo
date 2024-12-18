import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

class WebsiteProfileNextRankCard extends Interaction {
    static selector = ".o_wprofile_progress_circle";

    setup() {
        const tooltip = window.Tooltip.getOrCreateInstance(this.el.querySelector('g[data-bs-toggle="tooltip"]'));
        this.registerCleanup(() => tooltip.dispose());
    }
}

registry
    .category("public.interactions")
    .add("website_profile.website_profile_next_rank_card", WebsiteProfileNextRankCard);
