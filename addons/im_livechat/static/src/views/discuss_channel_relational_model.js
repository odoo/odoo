import { _t } from "@web/core/l10n/translation";
import { RelationalModel } from "@web/model/relational_model/relational_model";

export class DiscussChannelRelationalModel extends RelationalModel {
    async _loadGroupedList(config) {
        const { groups, length } = await super._loadGroupedList(config);
        if (config.groupBy[0] === "rating_last_value") {
            for (const group of groups) {
                switch (group.value) {
                    case 1:
                        group.displayName = _t("Unhappy");
                        break;
                    case 3:
                        group.displayName = _t("Neutral");
                        break;
                    case 5:
                        group.displayName = _t("Happy");
                        break;
                    default:
                        group.displayName = _t("Unrated");
                }
            }
        }
        return { groups, length };
    }
}
