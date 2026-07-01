import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

const filterMapping = {
    NEW: "ONGOING",
    ONGOING: "ONGOING",
    DONE: "SYNCED",
};

export class OrderTrackerDropdown extends Component {
    static template = "point_of_sale.OrderTrackerDropdown";
    static components = { Dropdown, DropdownItem };

    setup() {
        this.pos = usePos();
    }
    get externalOrderSummary() {
        return [];
    }
    getOptions(type, state) {
        return {};
    }
    getClass(type, state) {
        return "button-hover p-1 rounded";
    }
    // Shared methods used by both Self Order and Urban Piper
    goToOrders(serviceName, state, searchTerm = "") {
        this.pos.navigate("TicketScreen", {
            stateOverride: {
                search: {
                    fieldName: serviceName,
                    searchTerm: searchTerm,
                },
                filter: filterMapping[state],
            },
            ...this.getOptions(serviceName, state),
        });
    }
}
