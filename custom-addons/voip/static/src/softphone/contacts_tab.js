/* @odoo-module */

import { Component, onMounted, useState } from "@odoo/owl";

import { url } from "@web/core/utils/urls";
import { useService } from "@web/core/utils/hooks";

export class ContactsTab extends Component {
    static props = { extraClass: { type: String, optional: true } };
    static defaultProps = { extraClass: "" };
    static template = "voip.ContactsTab";

    setup() {
        this.store = useState(useService("mail.store"));
        this.voip = useState(useService("voip"));
        this.orm = useService("orm");
        this.personaService = useService("mail.persona");
        onMounted(() => this.voip.fetchContacts());
    }

    /** @returns {string} */
    getAvatarUrl(partner) {
        return url("/web/image", { model: "res.partner", id: partner.id, field: "avatar_128" });
    }

    onClickContact(ev, contact) {
        const partner = this.store.Persona.get(contact);
        this.voip.softphone.selectCorrespondence({ partner });
    }
}
