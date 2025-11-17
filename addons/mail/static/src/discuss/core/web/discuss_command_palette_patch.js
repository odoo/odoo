import { DiscussCommandPalette } from "@mail/discuss/core/public_web/discuss_command_palette";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

const commandCategoryRegistry = registry.category("command_categories");

const DISCUSS_MENTIONED = "DISCUSS_MENTIONED";
const DISCUSS_RECENT = "DISCUSS_RECENT";

commandCategoryRegistry
    .add(DISCUSS_MENTIONED, { namespace: "@", name: _t("Mentions") }, { sequence: 10 })
    .add(DISCUSS_RECENT, { namespace: "@", name: _t("Recent") }, { sequence: 20 });

patch(DiscussCommandPalette.prototype, {
    buildResults() {
        const importantChannels = this.store.getSelfImportantChannels();
        const recentChannels = this.store.getSelfRecentChannels();
        const mentionedSet = new Set();
        const recentSet = new Set();
        const CATEGORY_LIMIT = 3;
        if (!this.cleanedTerm) {
            const limitedMentioned = importantChannels.slice(0, CATEGORY_LIMIT);
            for (const channel of limitedMentioned) {
                this.commands.push(this.makeDiscussCommand(channel, DISCUSS_MENTIONED));
                if (channel.channel_type === "chat") {
                    mentionedSet.add(channel.correspondent.persona);
                } else {
                    mentionedSet.add(channel);
                }
            }
            const limitedRecent = recentChannels
                .filter(
                    (channel) =>
                        !mentionedSet.has(channel) &&
                        !mentionedSet.has(channel.correspondent?.persona)
                )
                .slice(0, CATEGORY_LIMIT);
            for (const channel of limitedRecent) {
                this.commands.push(this.makeDiscussCommand(channel, DISCUSS_RECENT));
                if (channel.channel_type === "chat") {
                    recentSet.add(channel.correspondent.persona);
                } else {
                    recentSet.add(channel);
                }
            }
        }
        super.buildResults(new Set([...mentionedSet, ...recentSet]));
    },
});
