/** @odoo-module */

import { ListRenderer } from "@web/views/list/list_renderer";
import { registry } from "@web/core/registry";
import { patch } from '@web/core/utils/patch';
import { useX2ManyCrud, useOpenX2ManyRecord, X2ManyFieldDialog } from "@web/views/fields/relational_utils";
import { X2ManyField } from "@web/views/fields/x2many/x2many_field";

const fieldRegistry = registry.category("fields");

patch(X2ManyFieldDialog.prototype, 'chatbot_script_step_sequence', {
    /**
     * Dirty patching of the 'X2ManyFieldDialog'.
     * It is done to force the "save and new" to close the dialog first, and then click again on
     * the "Add a line" link.
     * 
     * This is the only way (or at least the least complicated) to correctly compute the sequence
     * field, which is crucial when creating chatbot.steps, as they depend on each other.
     * 
     */
    async save({ saveAndNew }) {
        if (this.record.resModel !== 'chatbot.script.step') {
            return this._super(...arguments);
        }

        if (await this.record.checkValidity()) {
            this.record = (await this.props.save(this.record, { saveAndNew })) || this.record;
        } else {
            return false;
        }

        this.props.close();

        if (saveAndNew) {
            document.querySelector('.o_field_x2many_list_row_add a').click();
        }

        return true;
    }
});

export class ChatbotStepsOne2manyRenderer extends ListRenderer {
    /**
     * Small override to force column entries to be non-sortable.
     * Indeed, we want to force it being sorted on "sequence" at all times.
     */
    setup() {
        super.setup();

        for (const [, properties] of Object.entries(this.fields)) {
            properties.sortable = false;
        }
    }
}

export class ChatbotStepsOne2many extends X2ManyField {
    /**
     * Overrides the "openRecord" method to overload the save.
     *
     * Every time we save a sub-chatbot.script.step, we want to save the whole chatbot.script record
     * and form view.
     *
     * This allows the end-user to easily chain steps, otherwise he would have to save the
     * enclosing form view in-between each step addition.
     */
    setup() {
        super.setup();

        const { saveRecord, updateRecord } = useX2ManyCrud(
            () => this.list,
            this.isMany2Many
        );

        const openRecord = useOpenX2ManyRecord({
            resModel: this.list.resModel,
            activeField: this.activeField,
            activeActions: this.activeActions,
            getList: () => this.list,
            saveRecord: async (record) => {
                await saveRecord(record);
                await this.props.record.save({stayInEdition: true});
            },
            updateRecord: updateRecord,
        });

        this._openRecord = (params) => {
            const activeElement = document.activeElement;
            openRecord({
                ...params,
                onClose: () => {
                    if (activeElement) {
                        activeElement.focus();
                    }
                },
            });
        };
    }
};

fieldRegistry.add("chatbot_steps_one2many", ChatbotStepsOne2many);

ChatbotStepsOne2many.components = {
    ...X2ManyField.components,
    ListRenderer: ChatbotStepsOne2manyRenderer
};
