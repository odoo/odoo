/** @odoo-module **/

import { prettifyMessageContent } from "@mail/utils/common/format";

import { Component, useState } from "@odoo/owl";

import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import { ForwardedMessage } from "./forwarded_message";
import { ThreadIcon } from "./thread_icon";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class ForwardDialog extends Component {
    static components = { ForwardedMessage, ThreadIcon };
    static template = "mail.ForwardDialog";
    static props = {
        close: Function,
        message: Object,
        thread: Object,
    };

    setup() {
        this.store = useService("mail.store");
        this.message = useState({ text: "" });
        this.state = useState({
            search: "",
            selected: [],
        });
        this.isMobileOS = isMobileOS();
        this.toggleSelection = this.toggleSelection.bind(this);
        this.targets = [];
        this.buildSuggestions();
    }

    buildSuggestions() {
        // const recents = this.store.getSelfRecentChannels();
        this.targets = this.store.getSelfRecentChannels();
    }

    get filteredTargets() {
        const search = this.state.search.toLowerCase();
        return this.targets.filter(
            (t) => t.name.toLowerCase().includes(search) && t.id !== this.props.message.thread.id
        );
    }

    onSearch(ev) {
        this.state.search = ev.target.value;
    }

    clearSearch() {
        if (this.state.search) {
            this.state.search = "";
        }
    }

    toggleSelection(id) {
        const idx = this.state.selected.indexOf(id);
        if (idx === -1) {
            this.state.selected.push(id);
        } else {
            this.state.selected.splice(idx, 1);
        }
    }

    async confirm() {
        console.log("Forwarding to:", this.state.selected);
        console.log("Message:", this.message.text);
        const body = await prettifyMessageContent(this.message.text);
        await rpc("/mail/message/forward_to", {
            forwarded_from_id: this.props.message.id,
            current_body: body,
            target_channels_ids: this.state.selected,
            body_is_html: true,
        });
        this.__owl__.remove();
    }

    cancel() {
        this.__owl__.remove();
    }
}
