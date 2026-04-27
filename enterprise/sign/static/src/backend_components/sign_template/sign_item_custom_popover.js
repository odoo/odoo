/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Record } from "@web/model/record";
import {
    many2ManyTagsField,
    Many2ManyTagsField,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";

import { Component, useState } from "@odoo/owl";

const actionFieldsGet = {
    option_ids: { type: "many2many", relation: "sign.item.option", string: "Selected Options" },
    responsible_id: { type: "many2one", relation: "sign.item.role", string: "Responsible" },
};

function getActionActiveFields() {
    const activeFields = {};
    for (const fName of Object.keys(actionFieldsGet)) {
        if (actionFieldsGet[fName].type === "many2many") {
            const related = Object.fromEntries(
                many2ManyTagsField.relatedFields({ options: {} }).map((f) => [f.name, f])
            );
            activeFields[fName] = {
                related: {
                    activeFields: related,
                    fields: related,
                },
            };
        } else {
            activeFields[fName] = actionFieldsGet[fName];
        }
    }
    return activeFields;
}

export class SignItemCustomPopover extends Component {
    static template = "sign.SignItemCustomPopover";
    static components = {
        Record,
        Many2ManyTagsField,
        Many2OneField,
    };
    static props = {
        id: { type: Number },
        alignment: { type: String },
        header_title: {type: String },
        placeholder: { type: String },
        required: { type: Boolean },
        option_ids: { type: Array },
        responsible: { type: Number },
        onValidate: { type: Function },
        updateSelectionOptions: { type: Function },
        updateRoles: { type: Function },
        type: { type: String },
        onDelete: { type: Function },
        onClose: { type: Function },
        debug: { type: String },
        roles: { type: Object },
        close: { type: Function },
        num_options: {type: Number, optional: true},
        radio_set_id: {type: Number, optional: true},
    };

    setup() {
        this.alignmentOptions = [
            { title: _t("Left"), key: "left" },
            { title: _t("Center"), key: "center" },
            { title: _t("Right"), key: "right" },
        ];
        this.state = useState({
            alignment: this.props.alignment,
            placeholder: this.props.placeholder,
            required: this.props.required,
            option_ids: this.props.option_ids,
            responsible: this.props.responsible,
            num_options: this.props.num_options,
            radio_set_id: this.props.radio_set_id,
        });
        this.signItemFieldsGet = getActionActiveFields();
        this.typesWithAlignment = new Set(["text", "textarea"]);
    }

    handleNumOptionsChange(value) {
        if (Number(value) < 2) {
            return;
        }
        this.state['num_options'] = Number(value);
    }

    onChange(key, value) {
        this.state[key] = value;
    }

    onValidate() {
        this.props.onValidate(this.state);
    }

    get recordProps() {
        return {
            mode: "edit",
            resModel: "sign.item",
            resId: this.props.id,
            fieldNames: this.signItemFieldsGet,
            activeFields: this.signItemFieldsGet,
            onRecordChanged: async (record, changes) => {
                if (changes.option_ids) {
                    const ids = record.data.option_ids.currentIds;
                    this.state.option_ids = ids;
                    this.props.updateSelectionOptions(ids);
                }
                if (changes.responsible_id) {
                    const id = changes.responsible_id;
                    this.state.responsible = id;
                    this.props.updateRoles(id);
                }
            },
        };
    }

    getMany2XProps(record, fieldName) {
        return {
            name: fieldName,
            id: fieldName,
            record,
            readonly: false,
            canCreateEdit: false,
            canQuickCreate: true,
        };
    }

    getOptionsProps(record, fieldName) {
        return {
            ...this.getMany2XProps(record, fieldName),
            domain: [["available", "=", true]],
            noSearchMore: true,
        };
    }

    get showAlignment() {
        return this.typesWithAlignment.has(this.props.type);
    }
}
