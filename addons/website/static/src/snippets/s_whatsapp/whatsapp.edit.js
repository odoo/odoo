import { registry } from "@web/core/registry";
import { Whatsapp } from "./whatsapp.js";

export class WhatsappEdit extends Whatsapp {
    // In edit mode, we don't want redirection when clicking the send
    // as it would be disruptive for the user who is trying to edit the snippet.
    sendMessage() {}

    onKeydownMessage(ev) {
        ev.preventDefault();
    }
}

registry.category("public.interactions.edit").add("website.whatsapp", {
    Interaction: WhatsappEdit,
});
