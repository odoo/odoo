import { registry } from "@web/core/registry";

//This is to simulate a contact method being added from elsewhere
registry.category("website.team_board.contact_methods").add("email", "test@example.com");
registry.category("website.team_board.contact_methods").add("phone", "123456789");
