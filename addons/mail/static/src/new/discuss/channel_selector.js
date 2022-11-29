/** @odoo-module */

import { useMessaging } from "../messaging_hook";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { KeepLast } from "@web/core/utils/concurrency";
import { Component } from "@odoo/owl";

/**
 * return a concurrency safe/debounced version of fn argument
 * @param {(arg) => Promise<any>} fn
 */
function useDebouncedSearch(fn, delay = 250) {
    const keepLast = new KeepLast();
    return useDebounced((arg) => {
        return keepLast.add(fn(arg));
    }, delay);
}

export class ChannelSelector extends Component {
    setup() {
        this.messaging = useMessaging();
        this.orm = useService("orm");
        const search = useDebouncedSearch(this.fetchChannels.bind(this));
        this.autocompleteProps = {
            value: "",
            sources: [
                {
                    options: search,
                },
            ],
            placeholder: this.props.category.addTitle,
            onSelect: this.onSelect.bind(this),
        };
    }

    async fetchChannels(value) {
        value = value.trim();
        if (value) {
            if (this.props.category.id === "channels") {
                const domain = [
                    ["channel_type", "=", "channel"],
                    ["name", "ilike", value],
                ];
                const fields = ["name"];
                const results = await this.orm.searchRead("mail.channel", domain, fields, {
                    limit: 10,
                });
                const choices = results.map((channel) => {
                    return {
                        id: channel.id,
                        value: channel.id,
                        label: channel.name,
                    };
                });
                choices.push({
                    id: "__create__",
                    value: value,
                    label: `create: #${value}`,
                });
                return choices;
            }
            if (this.props.category.id === "chats") {
                const results = await this.orm.call("res.partner", "im_search", [value, 10]);
                return results.map((data) => {
                    return { id: data.id, value: data.id, label: data.name };
                });
            }
        }
        return [];
    }

    onSelect(choice) {
        choice = choice.__proto__; // hack to work around autcomplete bug. ouch
        if (choice.id === "__create__") {
            this.messaging.createChannel(choice.value);
        } else {
            if (this.props.category.id === "channels") {
                this.messaging.joinChannel(choice.id, choice.label);
            } else {
                this.messaging
                    .joinChat(choice.id)
                    .then((chat) => (this.messaging.state.discuss.threadId = chat.id));
            }
        }
        if (this.props.onSelect) {
            this.props.onSelect();
        }
    }
}

Object.assign(ChannelSelector, {
    components: { AutoComplete },
    props: ["category", "onSelect?"],
    template: "mail.channel_selector",
});
