import { makeKwArgs, models, serverState } from "@web/../tests/web_test_helpers";

export class CalendarFilters extends models.ServerModel {
    _name = "calendar.filters";

    init_partner_filters() {
        const ids = this.search([
            ["active", "=", true],
            ["user_id", "=", serverState.userId],
        ]);
        this.write(ids, { active: false });
    }

    update_partner_filters(partnerIds) {
        const requestedPartnerIds = new Set(partnerIds);
        const existing = this.search_read(
            [["user_id", "=", serverState.userId]],
            ["id", "active", "partner_id"],
            makeKwArgs({ context: { active_test: false } })
        );
        const existingPartnerIds = new Set(existing.map((filter) => filter.partner_id[0]));

        const newPartnerIds = [...requestedPartnerIds].filter(
            (id) => !existingPartnerIds.has(id)
        );
        const toActivate = existing.filter(
            (filter) => requestedPartnerIds.has(filter.partner_id[0]) && !filter.active
        );
        const toDeactivate = existing.filter(
            (filter) => !requestedPartnerIds.has(filter.partner_id[0]) && filter.active
        );

        if (newPartnerIds.length) {
            this.create(
                newPartnerIds.map((partner_id) => ({
                    active: true,
                    partner_id,
                    user_id: serverState.userId,
                }))
            );
        }
        if (toActivate.length) {
            this.write(
                toActivate.map((filter) => filter.id),
                { active: true }
            );
        }
        if (toDeactivate.length) {
            this.write(
                toDeactivate.map((filter) => filter.id),
                { active: false }
            );
        }
    }
}
