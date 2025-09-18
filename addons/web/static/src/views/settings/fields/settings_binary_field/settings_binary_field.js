// @ts-check

/** @module @web/views/settings/fields/settings_binary_field/settings_binary_field - BinaryField variant resolving download URLs via the related field's relation */

/** BinaryField variant that resolves download URLs via the related field's relation. */
import { registry } from "@web/core/registry";
import { BinaryField, binaryField } from "@web/fields/media/binary/binary_field";
export class SettingsBinaryField extends BinaryField {
    static template = "web.SettingsBinaryField";

    /**
     * Resolve download URL data using the related field's relation model and ID.
     * @returns {{ model: string, field: string, id: number } & Record<string, any>}
     */
    getDownloadData() {
        const related = this.props.record.fields[this.props.name].related;
        const [fieldName, relatedFieldName] = related.split(".");
        return {
            ...super.getDownloadData(),
            model: this.props.record.fields[fieldName].relation,
            field: relatedFieldName ?? fieldName,
            id: this.props.record.data[fieldName].id,
        };
    }
}

const settingsBinaryField = {
    ...binaryField,
    component: SettingsBinaryField,
};

registry.category("fields").add("base_settings.binary", settingsBinaryField);
