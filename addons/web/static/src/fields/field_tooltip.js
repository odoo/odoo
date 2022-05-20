/** @odoo-module **/

import fieldRegistry from "web.field_registry";

export function getTooltipInfo(params) {
    let widgetDescription = undefined;
    if (params.activeField.widget) {
        if (params.activeField.FieldComponent.name === "LegacyField") {
            const widget = fieldRegistry.get(params.activeField.widget);
            widgetDescription = widget.prototype.description;
        } else {
            widgetDescription = params.activeField.FieldComponent.description;
        }
    }

    const info = {
        viewMode: params.viewMode,
        resModel: params.resModel,
        debug: Boolean(odoo.debug),
        field: {
            label: params.field.string,
            name: params.field.name,
            help: params.help || params.field.help,
            type: params.field.type,
            widget: params.activeField.widget,
            widgetDescription,
            context: params.activeField.context,
            domain: params.activeField.domain,
            modifiers: JSON.stringify(params.activeField.modifiers),
            changeDefault: params.field.change_default,
            relation: params.field.relation,
            selection: params.field.selection,
            default: params.field.default,
        },
    };
    return JSON.stringify(info);
}
