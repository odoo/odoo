export function getTooltipInfo(params) {
    let widgetDescription = undefined;
    if (params.fieldInfo.widget) {
        widgetDescription = params.fieldInfo.field.displayName;
    }
    let domain = params.fieldInfo.domain || params.field.domain;
    let context = params.fieldInfo.context;
    if (domain && typeof domain !== "string") {
        domain = JSON.stringify(domain);
    }
    if (context && typeof context !== "string") {
        context = JSON.stringify(context);
    }

    const info = {
        viewMode: params.viewMode,
        resModel: params.resModel,
        debug: Boolean(odoo.debug),
        field: {
            name: params.field.name,
            label: params.field.string,
            help: params.fieldInfo.help ?? params.field.help,
            type: params.field.type,
            widget: params.fieldInfo.widget,
            widgetDescription,
            context,
            domain,
            invisible: params.fieldInfo.invisible,
            column_invisible: params.fieldInfo.column_invisible,
            readonly: params.fieldInfo.readonly,
            required: params.fieldInfo.required,
            changeDefault: params.field.change_default,
            relation: params.field.relation,
            model_field: params.field.model_field,
            selection: params.field.selection,
            default: params.field.default,
        },
    };
    return JSON.stringify(info);
}
