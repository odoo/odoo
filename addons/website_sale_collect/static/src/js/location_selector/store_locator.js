import { patch } from "@web/core/utils/patch";
import { locationBatchUtils } from "@website/builder/plugins/store_locator_utils";

// This patch provides the website snippet s_store_locator with the ability
// to read and display opening hours collected from stock.warehouse. The
// opening hours are formatted by `stock.warehouse.get_opening_hours_by_partner`.
patch(locationBatchUtils, {
    async updateCalendar(orm, locationsMap, idsToUpdate) {
        const openingHoursByPartner = await orm.call(
            "stock.warehouse",
            "get_opening_hours_by_partner",
            [idsToUpdate]
        );
        for (const [partnerId, openingHours] of Object.entries(openingHoursByPartner)) {
            const loc = locationsMap.get(parseInt(partnerId));
            loc.opening_hours = openingHours;
        }
    },
});
