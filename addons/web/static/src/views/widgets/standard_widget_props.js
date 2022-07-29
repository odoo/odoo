/** @odoo-module **/

export const standardWidgetProps = {
    readonly: { type: Boolean, optional: true },
    record: { type: Object },
    // TODO WOWL remove "node" once there are no more legacy widgets.
    // DO NOT USE THIS PROP IN NEW WIDGETS. USE extractProps() INSTEAD.
    node: { type: Object },
};
