import { _t } from "@web/core/l10n/translation";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { useX2ManyCrud, useOpenX2ManyRecord } from "@web/views/fields/relational_utils";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { useService } from '@web/core/utils/hooks';
import { onWillStart } from "@odoo/owl";


export class One2ManyTagsSkillsField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        BadgeTag,
    };
    static template = "hr_recruitment_skills.One2ManyTagsSkillsField";

    setup() {
        super.setup();
        const { saveRecord, updateRecord } = useX2ManyCrud(() => this.list, this.isMany2Many);
        this.actionService = useService("action");
        this.orm = useService('orm');

        onWillStart(async () => {
            const companyId = user.activeCompany.id;
            const skillTypes = await this.orm.searchRead(
                'hr.skill.type',
                ['|', ['company_id', '=', false], ['company_id', '=', companyId]],
                [],
                { limit: 1 },
            );
            this.anySkills = skillTypes.length > 0 ? true : false;
            this.defaultSkillType = skillTypes.length > 0 ? skillTypes[0] : null;
        });
        
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

    async skillTypesAction() {
        return this.actionService.doAction("hr_skills.hr_skill_type_action");
    }

    getTagProps(record) {
        const tagProps = {
            id: record.id,
            text: record.data.display_name,
            color: record.data.color,
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

    async onAdd({ context, editable } = {}) {
        return super.onAdd({
            editable,
            context: {
                ...context,
            }
        });
    }
}

export const one2ManyTagsSkillsField = {
    ...x2ManyField,
    component: One2ManyTagsSkillsField,
};

registry.category("fields").add("many2one_tags_skills", one2ManyTagsSkillsField);
