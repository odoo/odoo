import { Component, onWillStart, useEffect, useState, xml } from "@odoo/owl";

import { useAutofocus, useService } from "@web/core/utils/hooks";
import { useSequential } from "@mail/utils/common/hooks";
import { highlightText } from "@web/core/utils/html";
import { useDebounced } from "@web/core/utils/timing";
import { escapeRegExp } from "@web/core/utils/strings";
import { rpc } from "@web/core/network/rpc";
import { NavigableList } from "@mail/core/common/navigable_list";

export class ConversationTagEdit extends Component {
    static components = { NavigableList };
    static props = ["thread", "autofocus?", "close?"];
    static template = "im_livechat.ConversationTagEdit";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.store = useService("mail.store");
        this.inputRef = useAutofocus();
        this.sequential = useSequential();
        this.state = useState({
            selectableTags: [],
            searchStr: "",
        });
        this.debouncedFetchConversationTags = useDebounced(
            this.fetchConversationTags.bind(this),
            250
        );
        onWillStart(() => {
            this.fetchConversationTags();
        });
        useEffect(
            () => {
                this.debouncedFetchConversationTags();
            },
            () => [this.state.searchStr]
        );
    }

    get allSelectableTagNames() {
        return this.state.selectableTags.map((tag) => tag.name);
    }

    get allSelectedTagNames() {
        return this.props.thread.livechat_conversation_tag_ids.map((tag) => tag.name);
    }

    get remainingSelectableTags() {
        return this.state.selectableTags.filter(
            (tag) => !tag.in(this.props.thread.livechat_conversation_tag_ids)
        );
    }

    get navigableListProps() {
        return {
            onSelect: (ev, option) => {
                this.toggleSelectedTag(option.tag);
                this.state.searchStr = "";
            },
            optionTemplate: xml`<t t-out="option.label"/>`,
            options: this.remainingSelectableTags.map((tag) => ({
                tag,
                label: highlightText(this.state.searchStr.trim(), tag.name, "text-primary"),
                buttonClass: "btn",
            })),
        };
    }

    async toggleSelectedTag(tag) {
        await rpc("/im_livechat/conversation/update_tags", {
            channel_id: this.props.thread.id,
            tag_ids: [tag.id],
            method: this.props.thread.livechat_conversation_tag_ids.includes(tag)
                ? "DELETE"
                : "ADD",
        });
    }

    async fetchConversationTags() {
        const results = await this.sequential(() =>
            this.orm.searchRead(
                "im_livechat.conversation.tag",
                [["name", "ilike", this.state.searchStr]],
                ["id", "name"],
                { limit: 15 }
            )
        );
        if (!results) {
            return;
        }
        const result = this.store["im_livechat.conversation.tag"].insert(results);
        this.state.selectableTags = [...result];
    }

    onKeydownSearchInput(ev) {
        if (ev.key === "Enter") {
            if (!this.state.searchStr.trim()) {
                return;
            }
            ev.preventDefault();
            this.onClickCreateToggle();
        }
    }

    async onClickFooterSelectedTag(tag) {
        this.toggleSelectedTag(tag);
    }

    async onClickCreateToggle() {
        const tagName = this.state.searchStr.trim();
        const existingSelectableTag = this.state.selectableTags.find((tag) => tag.name === tagName);
        if (this.props.thread.livechat_conversation_tag_ids.includes(existingSelectableTag)) {
            return;
        }
        if (
            existingSelectableTag &&
            !this.props.thread.livechat_conversation_tag_ids.includes(existingSelectableTag)
        ) {
            this.toggleSelectedTag(existingSelectableTag);
            this.state.searchStr = "";
            return;
        }
        const [tagId] = await this.orm.create("im_livechat.conversation.tag", [
            { name: escapeRegExp(tagName) },
        ]);
        const newTag = this.store["im_livechat.conversation.tag"].insert({
            id: tagId,
            name: tagName,
        });
        this.state.selectableTags = [newTag, ...this.state.selectableTags];
        this.toggleSelectedTag(newTag);
        this.state.searchStr = "";
    }
}
