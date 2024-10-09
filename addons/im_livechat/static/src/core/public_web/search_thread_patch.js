import { SearchThread } from "@mail/discuss/core/public_web/search_thread";
import { cleanTerm } from "@mail/utils/common/format";
import { patch } from "@web/core/utils/patch";

patch(SearchThread.prototype, {
    get suggestions() {
        const suggestions = super.suggestions;
        const cleanedTerm = cleanTerm(this.state.searchValue);
        if (!cleanedTerm) {
            return suggestions;
        }
        if (!this.props.category || this.props.category === this.store.discuss.livechats) {
            suggestions.push(
                ...this.store.discuss.livechats
                    .filter((thread) => cleanTerm(thread.displayName).includes(cleanedTerm))
                    .map((thread) => {
                        return {
                            optionTemplate: "discuss.SearchThread.channel",
                            classList: "o-mail-SearchThread-suggestion",
                            channel: thread,
                            group: 20,
                        };
                    })
            );
        }
        return suggestions;
    },
    async onSelect(option) {
        if (option.channel?.channel_type === "livechat") {
            const channel = await this.store.Thread.getOrFetch(option.channel);
            channel.open();
            this.props.onCompleted?.();
            this.state.searchValue = "";
        } else {
            super.onSelect(option);
        }
    },
});
