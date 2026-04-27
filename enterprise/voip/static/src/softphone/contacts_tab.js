import { Component, onMounted, useState } from "@odoo/owl";

import { useVisible } from "@mail/utils/common/hooks";
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
        onMounted(() => this.voip.fetchContacts());
        const lastShownContactState = useVisible("last-shown-contact", (isVisible) => {
            if (lastShownContactState.isVisible) {
                this.voip.fetchContacts(
                    this.voip.softphone.searchBarInputValue.trim(),
                    this.voip.softphone.contacts.length
                );
            }
        });
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
