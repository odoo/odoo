/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Record } from "@web/model/record";
import {
    many2ManyTagsField,
    Many2ManyTagsField,
    Many2ManyTagsFieldColorEditable,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { Component, useRef } from "@odoo/owl";

const actionFieldsGet = {
    tag_ids: { type: "many2many", relation: "sign.template.tag", string: "Tags" },
    authorized_ids: { type: "many2many", relation: "res.users", string: "Authorized Users" },
    group_ids: { type: "many2many", relation: "res.groups", string: "Authorized Groups" },
};

function getActionActiveFields() {
    const activeFields = {};
    for (const fName of Object.keys(actionFieldsGet)) {
        const related = Object.fromEntries(
            many2ManyTagsField.relatedFields({ options: {} }).map((f) => [f.name, f])
        );
        activeFields[fName] = {
            related: {
                activeFields: related,
                fields: related,
            },
        };
    }
    activeFields.tag_ids.related.activeFields.color = { type: "integer", string: "Color" };
    return activeFields;
}

export class SignTemplateTopBar extends Component {
    static template = "sign.SignTemplateTopBar";
    static components = {
        Many2ManyTagsFieldColorEditable,
        Many2ManyTagsField,
        Record,
    };
    static props = {
        signTemplate: { type: Object },
        hasSignRequests: { type: Boolean },
        onTemplateNameChange: { type: Function },
        manageTemplateAccess: { type: Boolean },
    };

    setup() {
        this.displayNameInput = useRef("display-name");
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.signTemplateFieldsGet = getActionActiveFields();
    }

    changeInputSize() {
        const el = this.displayNameInput.el;
        if (el) {
            el.size = el.value.length + 1;
        }
    }

    get displayNameSize() {
        return this.props.signTemplate.display_name.length + 1;
    }

    editDisplayName() {
        this.displayNameInput.el.focus();
        this.displayNameInput.el.select();
    }

    onKeyDown(e) {
        if (e.key === "Enter") {
            this.displayNameInput.el.blur();
        }
    }

    onTemplatePropertiesClick() {
        this.action.doAction({
            name: "Edit Template Form",
            type: "ir.actions.act_window",
            res_model: "sign.template",
            res_id: this.props.signTemplate.id,
            views: [[false, "form"]],
        });
    }

    getMany2ManyProps(record, fieldName) {
        return {
            name: fieldName,
            id: fieldName,
            record,
            readonly: this.props.hasSignRequests,
        };
    }

    get recordProps() {
        return {
            mode: this.props.hasSignRequests ? "readonly" : "edit",
            onRecordChanged: (record, changes) => {
                this.saveChanges(record, changes);
            },
            resModel: "sign.template",
            resId: this.props.signTemplate.id,
            fieldNames: this.signTemplateFieldsGet,
            activeFields: this.signTemplateFieldsGet,
        };
    }

    async saveChanges(record, changes) {
        const res = await this.orm.call("sign.template", "write", [[record.resId], changes]);
        if (res) {
            this.notification.add(_t("Saved"), { type: "success" });
        }
    }
}
