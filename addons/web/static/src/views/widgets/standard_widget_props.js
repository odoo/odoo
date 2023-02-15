/** @odoo-module **/

export const standardWidgetProps = {
    readonly: { type: Boolean, optional: true },
    record: { type: Object },
    // TODO TO REMOVE - ListView - FGE
    options: { type: Object, optional: true },
    rawAttrs: { type: Object, optional: true },
    WidgetComponent: { type: Function, optional: true },
    className: { type: String, optional: true },
};
