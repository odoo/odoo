import { fields, getKwArgs, models } from "@web/../tests/web_test_helpers";

export class MailTestRottingResource extends models.ServerModel {
    _name = "mail.test.rotting.resource";

    is_rotting = fields.Boolean({ string: "Rotting" });

    /** @override (see mail.tracking.duration.mixin) */
    read_progress_bar() {
        const result = super.read_progress_bar(...arguments);
        const { domain, group_by } = getKwArgs(arguments, "domain", "group_by", "progress_bar");
        const rottingGroups = this.formatted_read_group(
            [...domain, ["is_rotting", "=", true]],
            [group_by],
            ["__count"]
        );
        result.__rotting_counts = Object.fromEntries(
            rottingGroups.map((group) => {
                const value = group[group_by];
                return [String(Array.isArray(value) ? value[0] : value), group.__count];
            })
        );
        return result;
    }
}
