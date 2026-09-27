import { registry } from "@web/core/registry";
import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";

export class SettingsBinaryField extends BinaryField {
    static template = "web.SettingsBinaryField";

    getDownloadData() {
        const related = this.props.record.fields[this.props.name].related;
        const [fieldName, relatedFieldName] = related.split(".");
        return {
            ...super.getDownloadData(),
            model: this.props.record.fields[fieldName].relation,
            field: relatedFieldName ?? fieldName,
            id: this.props.record.data[fieldName].id,
        }
    }

}

const settingsBinaryField = {
    ...binaryField,
    component: SettingsBinaryField,
};

registry.category("fields").add("base_settings.binary", settingsBinaryField);
