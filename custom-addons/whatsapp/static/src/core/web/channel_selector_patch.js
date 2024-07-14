/** @odoo-module **/

import { ChannelSelector } from "@mail/discuss/core/web/channel_selector";
import { cleanTerm } from "@mail/utils/common/format";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ChannelSelector.prototype, {
    async fetchSuggestions() {
        const cleanedTerm = cleanTerm(this.state.value);
        if (this.props.category.id === "whatsapp" && cleanedTerm) {
            const domain = [
                ["channel_type", "=", "whatsapp"],
                ["name", "ilike", cleanedTerm],
            ];
            const results = await this.sequential(() =>
                this.orm.searchRead("discuss.channel", domain, ["name"], {
                    limit: 10,
                })
            );
            if (!results) {
                this.state.navigableListProps.options = [];
                return;
            }
            const choices = results.map((channel) => {
                return {
                    channelId: channel.id,
                    classList: "o-mail-ChannelSelector-suggestion",
                    label: channel.name,
                };
            });
            if (choices.length === 0) {
                choices.push({
                    classList: "o-mail-ChannelSelector-suggestion",
                    label: _t("No results found"),
                    unselectable: true,
                });
            }
            this.state.navigableListProps.options = choices;
            return;
        }
        return super.fetchSuggestions();
    },

    onSelect(option) {
        if (this.props.category.id === "whatsapp") {
            this.threadService.openWhatsAppChannel(option.channelId, option.label);
            this.onValidate();
        } else {
            super.onSelect(option);
        }
    },
});
