/** @odoo-module native */
import { registry } from "@web/core/registry";
import { WebsitePage } from "@website/interactions/website_page";

// the page-level handlers (a shown modal marks itself `modal_shown`, zoomable
// images) belong to the page, not to the mode: the root widget they replaced
// kept them alive while editing
registry.category("public.interactions.edit").add("website.website_page", {
    Interaction: WebsitePage,
});
