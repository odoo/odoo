/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SlideQuestionListRenderer } from "./slide_question_list_renderer";
import { useOpenX2ManyRecord, useX2ManyCrud } from "@web/views/fields/relational_utils";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";

import { useSubEnv } from "@odoo/owl";


class SlideContentOneToManyField extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: SlideQuestionListRenderer,
    };
    setup() {
        super.setup();
        useSubEnv({ openRecord: this.openRecord.bind(this) });

        // Systematically and automatically save Slide Content at each Question edit/creation/deletion
        const { saveRecord, updateRecord } = useX2ManyCrud(() => this.list, this.isMany2Many);

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord: async (record) => {
                await saveRecord(record);
                await this.props.record.save();
            },
            updateRecord: updateRecord,
        });
        this._openRecord = async ({ record: paramRecord, ...params }) => {
            const { record } = this.props;
            if (!await record.save())
                // don't open question form as it can't be saved
                return;
            await openRecord({ record: paramRecord, ...params });
        };
        this.canOpenRecord = true;
    }
}

registry.category("fields").add("slide_question_one2many", {
    ...x2ManyField,
    component: SlideContentOneToManyField,
    additionalClasses: [...x2ManyField.additionalClasses || [], "o_field_one2many"],
});
