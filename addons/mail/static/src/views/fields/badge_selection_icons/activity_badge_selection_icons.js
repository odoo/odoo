import { useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { SIZES } from "@web/core/ui/ui_service";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { getFieldDomain } from "@web/model/relational_model/utils";
import { useSpecialData } from "@web/views/fields/relational_utils";
import {
    BadgeSelectionWithIconsField,
    badgeSelectionWithIconsField,
} from "./badge_selection_icons_field";

export class ActivityTypeBadgeIconsField extends BadgeSelectionWithIconsField {
    static template = "mail.ActivityTypeBadgeIconsField";

    setup() {
        super.setup();
        this.ui = useState(useService("ui"));
        this.specialData = useSpecialData(async (orm, props) => {
            const model = this.env.model.action.currentController?.props?.resModel;

            const user_activity_domain = [
                ["create_uid", "=", user.userId],
            ];

            if (model) {
                user_activity_domain.push(
                    "|",
                    ["res_model", "=", model],
                    ["res_model", "=", false]
                );
            } else {
                user_activity_domain.push(["res_model", "=", false]);
            }

            const grouped = await orm.call("mail.activity", "web_read_group", [], {
                domain: user_activity_domain,
                groupby: ["activity_type_id"],
                order: "__count desc",
                context: { active_test: false },
            });

            const domain = getFieldDomain(props.record, props.name, props.domain);
            const { relation } = props.record.fields[props.name];

            const ret = await orm.call(relation, "search_read", [], {
                domain,
                fields: ["id", "name", props.relatedIconField],
            });

            const orderMap = new Map(grouped.groups.map((g, i) => [g.activity_type_id?.[0], i]));
            ret.sort((a, b) => (orderMap.get(a.id) ?? Infinity) - (orderMap.get(b.id) ?? Infinity));

            return ret.map((opt) => {
                const iconValue = opt[props.relatedIconField] || props.defaultIcon;
                return [opt.id, opt.name, iconValue];
            });
        });
    }

    get visibleOptionCount() {
        return this.ui.size >= SIZES.XL ? 6 : 2;
    }

    get visibleOptions() {
        return this.options.slice(0, this.visibleOptionCount);
    }

    get overflowOptions() {
        return this.options.slice(this.visibleOptionCount);
    }
}

export const activityTypeBadgeIconsField = {
    ...badgeSelectionWithIconsField,
    component: ActivityTypeBadgeIconsField,
};

registry.category("fields").add("activity_type_badge_icons", activityTypeBadgeIconsField);
