import { Component, t, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";

export function extractM2OExtendedFieldProps(staticInfo, dynamicInfo) {
    return {
        ...extractM2OFieldProps(staticInfo, dynamicInfo),
        noSaveOnOpen: !!staticInfo.options.no_save_on_open,
    };
}

export function computeM2OExtendedProps(fieldProps) {
    const m2oProps = computeM2OProps(fieldProps);
    if (!fieldProps.noSaveOnOpen) {
        return m2oProps;
    }
    return {
        ...m2oProps,
        willOpenRecordInDialog: () => true,
        onRecordSaved: () => {
            const { name, record } = fieldProps;
            if (!record.isNew) {
                return m2oProps.onRecordSaved();
            }
            // A new record can't be reloaded. Setting the same id triggers the onchange, which
            // updates the fields computed from the related record.
            return record.update({ [name]: { id: record.data[name].id } });
        },
    };
}

export const many2OneExtendedFieldProps = {
    ...many2OneFieldProps,
    noSaveOnOpen: t.boolean().optional(),
};

/**
 * Many2one with the `no_save_on_open` option.
 *
 * In a dialog, the many2one of the framework can't open the related record without saving the main
 * record first. A new record is then created, and nothing opens when the record can't be saved.
 * With the option, the related record opens without saving, and the record is refreshed once the
 * related record is saved.
 */
export class Many2OneExtendedField extends Component {
    static template = "web.Many2OneField";
    static components = { Many2One };
    props = useProps(many2OneExtendedFieldProps);

    get m2oProps() {
        return computeM2OExtendedProps(this.props);
    }
}

registry.category("fields").add("many2one_extended", {
    ...buildM2OFieldDescription(Many2OneExtendedField),
    extractProps: extractM2OExtendedFieldProps,
});
