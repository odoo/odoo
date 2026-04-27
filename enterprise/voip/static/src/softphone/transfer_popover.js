import { Component, markup, onMounted, useRef, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";
import { escape, escapeRegExp } from "@web/core/utils/strings";
import { useDebounced } from "@web/core/utils/timing";

export class TransferPopover extends Component {
    static props = ["close", "defaultInputValue"];
    static template = "voip.TransferPopover";

    setup() {
        this.inputRef = useRef("input");
        this.userAgent = useService("voip.user_agent");
        this.voip = useService("voip");
        this.store = useState(useService("mail.store"));
        this.state = useState({ inputValue: this.props.defaultInputValue });
        this.onInputDebounced = useDebounced(
            () => this.voip.fetchContacts(this.state.inputValue),
            350
        );
        onMounted(() => this.inputRef.el.focus());
    }

    get recipientSuggestions() {
        const suggestions = [];
        const searchTerms = this.state.inputValue.toLowerCase();
        if (searchTerms === "") {
            return suggestions;
        }
        const contacts = Object.values(this.store.Persona.records).filter((x) => x.hasPhoneNumber);
        const regex = new RegExp(`(^.*)(${escapeRegExp(searchTerms)})(.*$)`, "i");
        for (const contact of contacts) {
            for (const key of ["displayName", "mobileNumber", "landlineNumber"]) {
                const value = contact[key];
                if (!value) {
                    continue;
                }
                const [, before, match, after] = (value.match(regex) ?? []).map(escape);
                if (!match) {
                    continue;
                }
                const suggestion = {
                    match: markup(`${before}<span class="fw-bold">${match}</span>${after}`),
                    phoneNumber: contact.mobileNumber || contact.landlineNumber,
                };
                if (key.endsWith("Number")) {
                    suggestion.match = markup(
                        `${escape(contact.displayName)} (${suggestion.match})`
                    );
                    suggestion.phoneNumber = contact[key];
                }
                suggestions.push(suggestion);
                break;
            }
        }
        return suggestions;
    }

    /** @param {MouseEvent} ev */
    onClickRecipient(ev) {
        this.state.inputValue = ev.target.dataset.number;
    }

    /** @param {KeyboardEvent} ev */
    onKeydown(ev) {
        if (ev.key === "Escape") {
            this.props.close();
        }
    }

    /** @param {KeyboardEvent} ev */
    onKeydownInput(ev) {
        if (ev.key === "Enter") {
            this.transfer();
        }
    }

    transfer() {
        if (this.state.inputValue === "") {
            return;
        }
        this.userAgent.transfer(this.state.inputValue);
        this.props.close();
    }
}
