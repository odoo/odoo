/** odoo-module */

import { Component } from "@odoo/owl";

export class PickupLocations extends Component {
    static template = "delivery.PickupLocations";

    static props = {
        locations: { type: Array },
        onSelectPickupPoint: { type: Function },
    };

    onSelectLocation(ev) {
        let location = this.props.locations.find(location => location.id === parseInt(ev.target.value));
        this.props.onSelectPickupPoint({
            id: location.pick_up_point_id,
            name: location.pick_up_point_name,
            street: location.pick_up_point_address,
            city: location.pick_up_point_town,
            zip: location.pick_up_point_postal_code,
            country: location.pick_up_point_country,
            state: location.pick_up_point_state,
            external_id: location.external_id
        });
    }

    showDistance() {
        return this.props.locations.some(location => location.distance);
    }
}
