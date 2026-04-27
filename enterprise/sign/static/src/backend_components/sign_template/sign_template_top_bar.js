/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Record } from "@web/model/record";
import {
    many2ManyTagsField,
    Many2ManyTagsField,
    Many2ManyTagsFieldColorEditable,
} from "@web/views/fields/many2many_tags/many2many_tags_field";
import { Component, useRef, useState } from "@odoo/owl";

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
        resModel: { type: String },
        isPDF: { type: Boolean },
    };

    setup() {
        this.displayNameInput = useRef("display-name");
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.signTemplateFieldsGet = getActionActiveFields();
        this.state = useState({
            properties: false,
        });
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

    /**
    * Saves the current signature document as sign template,
    * and updates the button's property state accordingly.
    *
    * @returns {Promise|boolean}
    */
    async onTemplateSaveClick() {
        const templateId = this.props.signTemplate.id;
        this.state.properties = await this.orm.call("sign.template", "write", [[templateId], { active: true }]);
        this.props.signTemplate.active = true;
        this.notification.add(_t("Document saved as Template."), { type: "success" });
        return this.state.properties;
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
        const result = await this.orm.write("sign.template", [record.resId], changes);
        return result;
    }

    get showEditButton() {
        return this.props.hasSignRequests && this.props.isPDF;
    }

    async editTemplate() {
        const duplicatedTemplateIds = await this.orm.call("sign.template", "copy", [
            [this.props.signTemplate.id],
        ]);

        this.action.doAction({
            type: "ir.actions.client",
            tag: "sign.Template",
            name: _t("Edit Template"),
            params: {
                id: duplicatedTemplateIds[0],
            },
        });
    }

}
