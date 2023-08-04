/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class ImportDataOptions extends Component {
    static template = "ImportDataOptions";
    static props = {
        importOptions: { type: Object, optional: true },
        fieldInfo: { type: Object },
        onOptionChanged: { type: Function },
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            options: [],
        });
        this.currentModel = this.props.fieldInfo.comodel_name || this.props.fieldInfo.model_name;
        onWillStart(async () => {
            this.state.options = await this.loadOptions();
        });
    }
    get isVisible() {
        return ["many2one", "many2many", "selection", "boolean"].includes(
            this.props.fieldInfo.type
        );
    }
    async loadOptions() {
        const options = [["prevent", _t("Prevent import")]];
        if (this.props.fieldInfo.type === "boolean") {
            options.push(["false", _t("Set to: False")]);
            options.push(["true", _t("Set to: True")]);
            !this.props.fieldInfo.required &&
                options.push(["import_skip_records", _t("Skip record")]);
        }
        if (["many2one", "many2many", "selection"].includes(this.props.fieldInfo.type)) {
            if (!this.props.fieldInfo.required) {
                options.push(["import_set_empty_fields", _t("Set value as empty")]);
                options.push(["import_skip_records", _t("Skip record")]);
            }
            if (this.props.fieldInfo.type === "selection") {
                const fields = await this.orm.call(this.currentModel, "fields_get");
                const selection = fields[this.props.fieldInfo.name].selection.map((opt) => [
                    opt[0],
                    _t("Set to: %s", opt[1]),
                ]);
                options.push(...selection);
            } else {
                options.push(["name_create_enabled_fields", _t("Create new values")]);
            }
        }
        return options;
    }
    onSelectionChanged(ev) {
        if (
            [
                "name_create_enabled_fields",
                "import_set_empty_fields",
                "import_skip_records",
            ].includes(ev.target.value)
        ) {
            this.props.onOptionChanged(
                ev.target.value,
                ev.target.value,
                this.props.fieldInfo.fieldPath
            );
        } else {
            const value = {
                fallback_value: ev.target.value,
                field_model: this.currentModel,
                field_type: this.props.fieldInfo.type,
            };
            this.props.onOptionChanged("fallback_values", value, this.props.fieldInfo.fieldPath);
        }
    }
}
