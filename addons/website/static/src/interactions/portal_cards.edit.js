import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class PortalCardsEdit extends Interaction {
    static selector = ".o_portal_cards";

    setup() {
        // Cards with a placeholder counter are hidden on the portal when there
        // are no matching records. In edit mode, show them anyway so they can be
        // identified, ordered, and toggled from the option.
        for (const placeholderEl of this.el.querySelectorAll("[data-placeholder_count]")) {
            const cardEl = placeholderEl.closest(".o_portal_index_card");
            if (cardEl.dataset.showInPortal !== "false") {
                cardEl.classList.remove("d-none");
            }
        }
    }
}

registry.category("public.interactions.edit").add("website.portal_cards", {
    Interaction: PortalCardsEdit,
});
