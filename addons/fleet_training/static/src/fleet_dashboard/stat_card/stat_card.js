import { Component, t, useProps } from "@odoo/owl";

export class FleetStatCard extends Component {
    static template = "fleet_training.FleetStatCard";

    props = useProps({
        label: t.string(),
        value: t.or([t.string(), t.number()]),
        icon: t.string(),
        color: t.string().optional(),
    });

    get color() {
        return this.props.color || "primary";
    }
}
