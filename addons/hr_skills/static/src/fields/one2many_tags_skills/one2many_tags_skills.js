import { _t } from "@web/core/l10n/translation";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { useX2ManyCrud, useOpenX2ManyRecord } from "@web/views/fields/relational_utils";
import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags_list/tags_list";

export class One2ManyTagsSkillsField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        TagsList,
    };
    static template = "hr_recruitment_skills.One2ManyTagsSkillsField";

    setup() {
        super.setup();
        const { saveRecord, updateRecord } = useX2ManyCrud(() => this.list, this.isMany2Many);

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord: saveRecord,
            updateRecord: updateRecord,
            withParentId: this.props.widget !== "many2many",
        });

        this._openRecord = (params) => {
            params.title = _t("Select Skills");
            openRecord({ ...params });
        };
    }

    getTagProps(record) {
        const tagProps = {
            id: record.id,
            resId: record.resId,
            text: record.data.display_name,
            colorIndex: record.data.color,
            canEdit: true,
            onClick: (ev) => this.onTagClick(ev, record),
            onDelete: !this.props.readonly ? () => this.activeActions.onDelete(record) : undefined,
        };
        return tagProps;
    }

    get tags() {
        return this.props.record.data[this.props.name].records.map((record) =>
            this.getTagProps(record)
        );
    }

    onTagClick(ev, record) {
        this.openRecord(record);
    }
}

export const one2ManyTagsSkillsField = {
    ...x2ManyField,
    component: One2ManyTagsSkillsField,
};

registry.category("fields").add("many2one_tags_skills", one2ManyTagsSkillsField);
