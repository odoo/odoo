import { registry } from "@web/core/registry";

registry
    .category("website.s_team_board.contact_methods")
    .add("email", { contactType: "email", contactData: "hello@world.com" });
