/** @odoo-module **/

import fieldRegistry from "web.field_registry";

export function getTooltipInfo(params) {
    let widgetDescription = undefined;
    if (params.fieldInfo.widget) {
        if (params.fieldInfo.FieldComponent.name === "LegacyField") {
            const widget = fieldRegistry.get(params.fieldInfo.widget);
            widgetDescription = widget.prototype.description;
        } else {
            widgetDescription = params.fieldInfo.FieldComponent.description;
        }
    }

    const info = {
        viewMode: params.viewMode,
        resModel: params.resModel,
        debug: Boolean(odoo.debug),
        field: {
            label: params.field.string,
            name: params.field.name,
            help: params.fieldInfo.help !== null ? params.fieldInfo.help : params.field.help,
            type: params.field.type,
            widget: params.fieldInfo.widget,
            widgetDescription,
            context: params.fieldInfo.context,
            domain: params.fieldInfo.domain,
            modifiers: JSON.stringify(params.fieldInfo.modifiers),
            changeDefault: params.field.change_default,
            relation: params.field.relation,
            selection: params.field.selection,
            default: params.field.default,
        },
    };
    return JSON.stringify(info);
}
