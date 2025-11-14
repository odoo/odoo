import { Component } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";

const { DateTime } = luxon;

export class PosSelfOrderTopAlert extends Component {
    static template = "pos_self_order.TopAlert";
    static props = {
        activeSlot: { validate: (s) => s === null || typeof s === "string" },
    };

    setup() {
        this.selfOrder = useSelfOrder();
    }

    get show() {
        const currentPage = this.props.activeSlot;
        const hideAlertOnPages = ["default", "location"];

        // Hide ...
        return !(
            (
                (currentPage && hideAlertOnPages.includes(currentPage)) || // ... on specific pages
                this.selfOrder.session || // ... if a session exists
                this.selfOrder.menuOnlyMode
            ) // ... if the mode is consultation only
        );
    }

    get message() {
        const preset = this.selfOrder.currentOrderPreset;
        const nextSlot = preset?.getNextSlotAcrossDays();
        if (!preset?.use_timing || !nextSlot) {
            return "We are currently closed but you can still have a look at the menu.";
        }

        const now = DateTime.now();
        const diffDays = nextSlot.datetime.diff(now, "days").days;
        const localized = nextSlot.datetime.setLocale(nextSlot.datetime.loc.locale);

        // Same day
        if (diffDays < 1) {
            const str_datetime = localized.toLocaleString({
                hour: "numeric",
                minute: "numeric",
            });

            return `The next available slot is at ${str_datetime}.`;
        }

        // Tomorrow
        if (diffDays < 2) {
            const str_datetime = localized.toLocaleString({
                hour: "numeric",
                minute: "numeric",
            });
            return `The next available slot is tomorrow at ${str_datetime}.`;
        }

        // Within a week
        if (diffDays <= 7) {
            const str_datetime = localized.toLocaleString({
                hour: "numeric",
                minute: "numeric",
                weekday: "long",
                day: "numeric",
            });
            return `The next available slot is on ${str_datetime}.`;
        }

        // Beyond a week
        const str_datetime = localized.toLocaleString({
            day: "numeric",
            month: "short",
            hour: "numeric",
            minute: "numeric",
        });
        return `The next available slot is on ${str_datetime}.`;
    }
}
