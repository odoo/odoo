/** @odoo-module **/

export function getTooltipInfo(params) {
    let widgetDescription = undefined;
    if (params.fieldInfo.widget) {
        widgetDescription = params.fieldInfo.field.displayName;
    }

    const info = {
        viewMode: params.viewMode,
        resModel: params.resModel,
        debug: Boolean(odoo.debug),
        field: {
            name: params.field.name,
            help: params.fieldInfo.help ?? params.field.help,
            type: params.field.type,
            widget: params.fieldInfo.widget,
            widgetDescription,
            context: params.fieldInfo.context,
            domain: params.fieldInfo.domain || params.field.domain,
            invisible: params.fieldInfo.invisible,
            column_invisible: params.fieldInfo.column_invisible,
            readonly: params.fieldInfo.readonly,
            required: params.fieldInfo.required,
            changeDefault: params.field.change_default,
            relation: params.field.relation,
            selection: params.field.selection,
            default: params.field.default,
        },
    };
    return JSON.stringify(info);
}
