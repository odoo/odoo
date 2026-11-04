import { Plugin, t, useConfig } from "@odoo/owl";
import { Domain } from "@web/core/domain";

/**
 * Filters of the ticket screen, checked in memory (`matches`) or on the server (`toDomain`):
 * both must match the same orders.
 */
export class TicketOrderFilters extends Plugin {
    /** @type {import("@point_of_sale/app/services/pos_store").PosStore} */
    pos = useConfig("pos", t.object());
    state = useConfig("state", t.object());
    getSearchFields = useConfig("getSearchFields", t.function());

    /** The filters set on the screen. */
    get values() {
        const { fieldName, searchTerm, partnerId } = this.state.search;
        return {
            status: this.state.filter,
            searchFieldName: fieldName,
            searchTerm,
            partnerId: fieldName === "PARTNER" ? partnerId : null,
            presetId: this.state.selectedPreset?.id || null,
        };
    }

    /** Clears the search and the preset, keeping the status. */
    clear() {
        this.state.search = { fieldName: this.state.search.fieldName, searchTerm: "" };
        this.state.selectedPreset = null;
    }

    /** Whether the order in memory matches the filters. */
    matches(order, values, searchFields = this.getSearchFields()) {
        if (!this.matchesStatus(order, values.status)) {
            return false;
        }
        if (values.partnerId) {
            if (order.partner_id?.id !== values.partnerId) {
                return false;
            }
        } else if (values.searchTerm) {
            const searchField = searchFields[values.searchFieldName];
            const searchTerm = values.searchTerm.trim().toLowerCase();
            const matches = (value) =>
                String(value ?? "")
                    .toLowerCase()
                    .includes(searchTerm);
            if (![searchField?.repr(order)].flat().some(matches)) {
                return false;
            }
        }
        if (values.presetId && order.preset_id?.id !== values.presetId) {
            return false;
        }
        return true;
    }

    /** Domain of the orders on the server matching the filters. */
    toDomain(values) {
        return Domain.and([
            this._getStatusDomain(values.status),
            this._getSearchDomain(values),
            values.presetId ? [["preset_id", "=", values.presetId]] : [],
        ]);
    }

    // ----- Status ----- //

    /** Whether the order has the status (Active, Paid, Cancelled or a status under Active). */
    matchesStatus(order, status) {
        if (status === "SYNCED") {
            return order.isPaid;
        }
        if (status === "CANCELLED") {
            return order.isCancelled;
        }
        const screen = order.getScreenData();
        const isActive = (!order.isPaid && !order.isCancelled) || screen.name === "TipScreen";
        if (!isActive || !status || status === "ACTIVE_ORDERS") {
            return isActive;
        }
        return this.getScreenToStatusMap()[screen.name] === status;
    }

    /** Domain version of `matchesStatus`. */
    _getStatusDomain(status) {
        if (status === "SYNCED") {
            return new Domain([["state", "in", ["paid", "done"]]]);
        }
        if (status === "CANCELLED") {
            return new Domain([["state", "=", "cancel"]]);
        }
        return new Domain([["state", "=", "draft"]]);
    }

    /** Maps the screen an active order is on to its status. */
    getScreenToStatusMap() {
        return {
            ProductScreen: "ONGOING",
            PaymentScreen: this.pos.config.set_tip_after_payment ? "OPEN" : "PAYMENT",
            TipScreen: "TIPPING",
        };
    }

    // ----- Search ----- //

    /** Domain version of the search and partner part of `matches`. */
    _getSearchDomain(values) {
        if (values.partnerId) {
            return new Domain([["partner_id", "=", values.partnerId]]);
        }
        let searchTerm = values.searchTerm?.trim();
        const searchField = this.getSearchFields()[values.searchFieldName];
        if (!searchTerm || !searchField?.modelFields?.length) {
            return new Domain([]);
        }
        if (searchField.formatSearch) {
            searchTerm = searchField.formatSearch(searchTerm);
        }
        return Domain.or(
            searchField.modelFields.map((modelField) => [[modelField, "ilike", searchTerm]])
        );
    }
}
