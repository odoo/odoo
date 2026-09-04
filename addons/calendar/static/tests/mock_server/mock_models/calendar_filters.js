import { models, serverState } from "@web/../tests/web_test_helpers";

export class CalendarFilters extends models.ServerModel {
    _name = "calendar.filters";

    init_partner_filters() {
        const ids = this.search([
            ["user_id", "=", serverState.userId],
            ["partner_checked", "=", true],
        ]);
        this.write(ids, { partner_checked: false });
    }

    update_partner_filters(partnerIds) {
        const requestedPartnerIds = new Set(partnerIds);
        const existing = this.search_read([["user_id", "=", serverState.userId]], {
            context: { active_test: false },
            fields: ["id", "partner_id", "active", "partner_checked"],
        });
        const existingPartnerIds = new Set(existing.map((filter) => filter.partner_id[0]));

        const newPartnerIds = [...requestedPartnerIds].filter(
            (id) => !existingPartnerIds.has(id)
        );
        const toActivate = existing.filter(
            (filter) =>
                requestedPartnerIds.has(filter.partner_id[0]) &&
                !(filter.active && filter.partner_checked)
        );
        const toDeactivate = existing.filter(
            (filter) =>
                !requestedPartnerIds.has(filter.partner_id[0]) &&
                filter.active &&
                filter.partner_checked
        );

        if (newPartnerIds.length) {
            this.create(
                newPartnerIds.map((partner_id) => ({
                    active: true,
                    partner_id,
                    partner_checked: true,
                    user_id: serverState.userId,
                }))
            );
        }
        if (toActivate.length) {
            this.write(
                toActivate.map((filter) => filter.id),
                { active: true, partner_checked: true }
            );
        }
        if (toDeactivate.length) {
            this.write(
                toDeactivate.map((filter) => filter.id),
                { active: false, partner_checked: false }
            );
        }
    }
}
