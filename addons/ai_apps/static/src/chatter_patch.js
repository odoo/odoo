import { Chatter } from "@mail/chatter/web_portal/chatter";
import { _t } from "@web/core/l10n/translation";

import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";

/**
 * @type {import("@mail/chatter/web_portal/chatter").Chatter }
 * @typedef {Object} Props
 * @property {function} [close]
 */
patch(Chatter.prototype, {
    setup() {
        super.setup();
    },
    /**
     * Converts record data to JSON, so we can pass them to the AI record's context
     * @returns {String} String JSON representation of the record
     */
    recordDataToJSON(recordData, fieldsInfo) {
        const result = {};

        for (const fieldName in recordData) {
            if (!recordData.hasOwnProperty(fieldName)) continue;
            const fieldValue = recordData[fieldName];
            const fieldInfo = fieldsInfo[fieldName] || {};
            // Skip binary fields entirely - there is no easy way of placing them in the context
            if (fieldInfo.type === 'binary') {
                continue;
            }
            // Handle relational fields
            if (['many2one', 'many2many', 'one2many'].includes(fieldInfo.type)) {
                // Skip abnormally large relational fields which can floud the AI context
                if (fieldValue && fieldValue.records && fieldValue.records.length > 50) {
                    continue;
                }
                switch (fieldInfo.type) {
                    case 'many2one':
                        result[fieldName] = fieldValue ? fieldValue.display_name || fieldValue.name : null;
                        break;
                    case 'many2many':
                    case 'one2many':
                        if (fieldValue && fieldValue.records) {
                            result[fieldName] = fieldValue.records.map(record => 
                                record.data.display_name || record.data.name
                            );
                        } else {
                            result[fieldName] = [];
                        }
                        break;
                }
            } else if (fieldInfo.type === 'date' && fieldValue) {  // handle date fields
                const date = luxon.DateTime.fromISO(fieldValue);
                result[fieldName] = date.isValid ? formatDate(date) : fieldValue;
            } else if (fieldInfo.type === 'datetime' && fieldValue) {  // handle datetime fields
                const datetime = luxon.DateTime.fromISO(fieldValue);
                result[fieldName] = datetime.isValid ? formatDateTime(datetime) : fieldValue;
            } else {  // handle all other types of fields
                result[fieldName] = fieldValue;
            }
        }
        return result;
    },
    async onClickAIChatterButton() {
        // Force save the record so we can fetch chatter messages from the back-end
        const saved = await this.props.record.save();
        if (!saved) {
            return;
        }
        const recordInfo = this.recordDataToJSON(this.props.record.data, this.props.record.fields);
        const ai_channel_id = await this.orm.call(
            'discuss.channel',
            'create_ai_composer_channel',
            [ 
                'chatter_ai_button',
                recordInfo.name,
                this.props.record.resModel,
                this.props.record.resId,
                JSON.stringify(recordInfo),
            ], 
        );
        const thread = await this.store.Thread.getOrFetch({
            model: "discuss.channel",
            id: Number(ai_channel_id), 
        });
        thread.composerText = _t('Summarize the chatter conversation');
        thread.aiSpecialActions = {
            'sendMessage': (content) => {
                this.state.thread.post(content);
            },
            'logNote': (content) => {
                this.state.thread.post(content, { 'isNote': true });
            }
        };
        thread.open({ 
            focus: true,
        });
        return;
    },
});
