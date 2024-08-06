import { SearchMessagesPanel } from "@mail/core/common/search_messages_panel";
import { patch } from "@web/core/utils/patch";
import { cleanTerm } from "@mail/utils/common/format";
import { Activity } from "@mail/core/web/activity";
import { _t } from "@web/core/l10n/translation";

Object.assign(SearchMessagesPanel.components, {
    Activity,
});

/**
 * @type {import("@mail/core/common/search_messages_panel").SearchMessagesPanel }
 */
patch(SearchMessagesPanel.prototype, {
    setup() {
        super.setup(...arguments);
        Object.assign(this.state, {
            activities: [],
        });
    },

    get ACTIVITIES_FOUND() {
        if (!this.messageSearch.searched || !this.env.inChatter) {
            return false;
        }
        if (!this.state.activities.length) {
            return _t("No activities found");
        }
        return _t("%s activities found", this.state.activities.length);
    },

    search() {
        super.search(...arguments);
        const cleanSearchTerm = cleanTerm(this.state.searchTerm);
        this.state.activities = this.props.thread.activities.filter(
            (activity) =>
                activity.activity_type_id[1].toLowerCase().includes(cleanSearchTerm) ||
                (activity.summary && activity.summary.toLowerCase().includes(cleanSearchTerm)) ||
                (activity.note && activity.note.toLowerCase().includes(cleanSearchTerm))
        );
    },
});
