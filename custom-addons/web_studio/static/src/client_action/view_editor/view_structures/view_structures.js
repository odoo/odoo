/** @odoo-module */
import { Component, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

export class ExistingFields extends Component {
    static props = {
        fieldsInArch: { type: Array },
        fields: { type: Object },
        filterFields: { type: Boolean, optional: true },
        folded: { type: Boolean, optional: true },
        resModel: { type: String, optional: true },
    };
    static defaultProps = {
        folded: true,
        filterFields: true,
        resModel: "",
    };
    static template = "web_studio.ViewStructures.ExistingFields";

    setup() {
        this.state = useState({
            folded: this.props.folded,
            searchValue: "",
        });
    }

    isMatchingSearch(field) {
        if (!this.state.searchValue) {
            return true;
        }
        const search = this.state.searchValue.toLowerCase();
        let matches = field.string.toLowerCase().includes(search);
        if (!matches && this.env.debug && field.name) {
            matches = field.name.toLowerCase().includes(search);
        }
        return matches;
    }

    get existingFields() {
        const fieldsInArch = this.props.fieldsInArch;
        const resModel = this.props.resModel;
        const filtered = Object.entries(this.props.fields).filter(([fName, field]) => {
            if (resModel === "res.users" && (fName.startsWith("in_group_") || fName.startsWith("sel_groups_"))) {
                // These fields are virtual and represent res.groups hierarchy.
                // If the hierarchy changes, the field is replaced by another one and the view will be
                // broken, so, here we prevent adding them.
                return false;
            }
            if (!this.isMatchingSearch(field) || this.props.filterFields && fieldsInArch.includes(fName)) {
                return false;
            }
            return true;
        });

        return filtered.map(([fName, field]) => {
            return {
                ...field,
                name: fName,
                classType: field.type,
                dropData: JSON.stringify({ fieldName: fName }),
            };
        });
    }

    getDropInfo(field) {
        return {
            structure: "field",
            fieldName: field.name,
            isNew: false,
        };
    }
}

const newFields = [
    { type: "char", string: _t("Text") },
    { type: "text", string: _t("Multine Text") },
    { type: "integer", string: _t("Integer") },
    { type: "float", string: _t("Decimal") },
    { type: "html", string: _t("HTML") },
    { type: "monetary", string: _t("Monetary") },
    { type: "date", string: _t("Date") },
    { type: "datetime", string: _t("Datetime") },
    { type: "boolean", string: _t("CheckBox") },
    { type: "selection", string: _t("Selection") },
    { type: "binary", string: _t("File"), widget: "file" },
    { type: "one2many", string: _t("Lines"), special: "lines" },
    { type: "one2many", string: _t("One2Many") },
    { type: "many2one", string: _t("Many2One") },
    { type: "many2many", string: _t("Many2Many") },
    { type: "binary", string: _t("Image"), widget: "image", name: "picture" },
    { type: "many2many", string: _t("Tags"), widget: "many2many_tags", name: "tags" },
    { type: "selection", string: _t("Priority"), widget: "priority" },
    { type: "binary", string: _t("Signature"), widget: "signature" },
    { type: "related", string: _t("Related Field") },
];

export class NewFields extends Component {
    static props = {};
    static template = "web_studio.ViewStructures.NewFields";

    get newFieldsComponents() {
        return newFields.map((f) => {
            const classType = f.special || f.name || f.widget || f.type;
            return {
                ...f,
                name: classType,
                classType,
                dropData: JSON.stringify({
                    fieldType: f.type,
                    widget: f.widget,
                    name: f.name,
                    special: f.special,
                    string: f.string,
                }),
            };
        });
    }
}
