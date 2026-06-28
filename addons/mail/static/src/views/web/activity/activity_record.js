import { ActivityCompiler } from "@mail/views/web/activity/activity_compiler";

import { Component, props, types } from "@odoo/owl";

import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { user } from "@web/core/user";
import { isHtmlEmpty } from "@web/core/utils/html";
import { imageUrl } from "@web/core/utils/urls";
import { Field } from "@web/views/fields/field";
import { fileTypeMagicWordMap } from "@web/views/fields/image/image_field";
import { getFormattedRecord } from "@web/views/kanban/kanban_record";
import { useViewCompiler } from "@web/views/view_compiler";
import { Record } from "@web/model/relational_model/record";

/**
 * Returns the image URL of a given field on the record.
 *
 * @param {Record} record
 * @param {string} [model] model name
 * @param {string} [field] field name
 * @param {number | [number, ...any[]]} [idOrIds] id or array
 *      starting with the id of the desired record.
 * @param {string} [placeholder] fallback when the image does not
 *  exist
 * @returns {string}
 */
export function getImageSrcFromRecordInfo(record, model, field, idOrIds, placeholder) {
    const id = (Array.isArray(idOrIds) ? idOrIds[0] : idOrIds) || null;
    const isCurrentRecord =
        record.resModel === model && (record.resId === id || (!record.resId && !id));
    const fieldVal = record.data[field];
    if (isCurrentRecord && fieldVal && !isBinSize(fieldVal)) {
        // Use magic-word technique for detecting image type
        const type = fileTypeMagicWordMap[fieldVal[0]];
        return `data:image/${type};base64,${fieldVal}`;
    } else if (placeholder && (!model || !field || !id || !fieldVal)) {
        // Placeholder if either the model, field, id or value is missing or null.
        return placeholder;
    } else {
        // Else: fetches the image related to the given id.
        const unique = isCurrentRecord && record.data.write_date;
        return imageUrl(model, id, field, { unique });
    }
}

function isBinSize(value) {
    return /^\d+(\.\d*)? [^0-9]+$/.test(value);
}

export class ActivityRecord extends Component {
    static components = {
        Field,
    };
    static template = "mail.ActivityRecord";

    setup() {
        this.props = props({
            archInfo: types.object({
                fieldNodes: types.record(),
                templateDocs: types.record(),
                title: types.string(),
            }),
            openRecord: types.function([
                types.instanceOf(Record),
                types.object({ newWindow: types.boolean().optional() }),
            ]),
            record: types.instanceOf(Record),
        });
        this.evaluateBooleanExpr = evaluateBooleanExpr;
        this.widget = {
            deletable: false,
            editable: false,
            isHtmlEmpty,
        };
        const { templateDocs } = this.props.archInfo;
        const templates = useViewCompiler(ActivityCompiler, templateDocs);
        this.recordTemplate = templates["activity-box"];
    }

    getRenderingContext() {
        const { record } = this.props;
        return {
            record: getFormattedRecord(record),
            activity_image: (...args) => getImageSrcFromRecordInfo(record, ...args),
            user_context: user.context,
            widget: this.widget,
            luxon,
            __comp__: Object.assign(Object.create(this), { this: this }),
        };
    }
}
