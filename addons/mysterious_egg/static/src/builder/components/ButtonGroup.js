import { Component, EventBus, useSubEnv } from "@odoo/owl";

export class ButtonGroup extends Component {
    static template = "mysterious_egg.ButtonGroup";
    static props = {
        activeState: { type: Object, optional: true },
        isActive: { type: Boolean, optional: true },
        onClick: { type: Function, optional: true },
        slots: { type: Object, optional: true },
    };

    setup() {
        const bus = new EventBus();
        useSubEnv({
            buttonGroupBus: bus,
        });
    }
}
