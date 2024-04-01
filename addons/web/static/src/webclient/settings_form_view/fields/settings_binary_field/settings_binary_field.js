/** @odoo-module **/

import { registry } from "@web/core/registry";
import { BinaryField, binaryField } from "@web/views/fields/binary/binary_field";

export class SettingsBinaryField extends BinaryField {
    static template = "web.SettingsBinaryField";

    getDownloadData() {
        const related = this.props.record.fields[this.props.name].related;
        return {
            ...super.getDownloadData(),
            model: this.props.record.fields[related.split(".")[0]].relation,
            field: related.split(".")[1] ?? related.split(".")[0],
            id: this.props.record.data[related.split(".")[0]][0],
        }
    }

}

const settingsBinaryField = {
    ...binaryField,
    component: SettingsBinaryField,
};

registry.category("fields").add("base_settings.binary", settingsBinaryField);
