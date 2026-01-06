import { FormOptionPlugin, SetFormCustomFieldValueListAction } from "@website/builder/plugins/form/form_option_plugin";
import { patch } from "@web/core/utils/patch";
import { getActiveField, getSelect } from "@website/builder/plugins/form/utils";

patch(FormOptionPlugin.prototype, {
    async _fetchFieldRecords(field) {
        if (!field) {
            return super._fetchFieldRecords(field)
        }
        if (field.field.name === "applicant_skill_ids") {
            return field.field.skill_types;
        }
        return super._fetchFieldRecords(field);
    },
});

patch(SetFormCustomFieldValueListAction.prototype, {
    async apply({ editingElement: fieldEl, value, loadResult: fields }) {
        const field = getActiveField(fieldEl, { fields });
        if (field.name !== "applicant_skill_ids") {
            return await super.apply(...arguments);
        }

        let valueList = JSON.parse(value);
        if (getSelect(fieldEl)) {
            valueList = valueList.filter(v => v.id || v.display_name);
            const hasDefault = valueList.some(v => v.selected);
            if (valueList.length && !hasDefault) {
                valueList.unshift({ id: "", display_name: "", selected: true });
            }
        }

        field.records = valueList;
        const selectedTypeIds = valueList.filter(tp => tp.selected).map(tp => tp.id);
        field.selectedSkills = field.skill_types.filter(tp => selectedTypeIds.includes(tp.id)).flatMap(tp => tp.skill_ids);
        this.dependencies.websiteFormOption.replaceField(fieldEl, field, fields);
    },
});
