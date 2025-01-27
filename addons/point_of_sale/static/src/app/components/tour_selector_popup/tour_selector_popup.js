import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class TourSelectorPopup extends Component {
    static components = { Dialog };
    static template = "point_of_sale.TourSelectorPopup";
    static props = ["close", "getPayload"];

    setup() {
        this.pos = usePos();
        this.state = useState({
            selectedTours: new Set(),
        });
    }

    get tours() {
        const tourNames = Object.keys(registry.subRegistries["web_tour.tours"].content);
        return tourNames.filter((name) => name.includes("PoSFakeTour"));
    }

    onCheck(ev) {
        return ev.target.checked
            ? this.state.selectedTours.add(ev.target.id)
            : this.state.selectedTours.delete(ev.target.id);
    }

    confirm() {
        this.props.getPayload([...this.state.selectedTours]);
        this.props.close();
    }
}
