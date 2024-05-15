import { registry } from "@web/core/registry";
import { imageUrl } from "@web/core/utils/urls";
import { fileTypeMagicWordMap } from "@web/views/fields/image/image_field";
import { standardWidgetProps } from "../standard_widget_props";

import { Component } from "@odoo/owl";

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

class KanbanImage extends Component {
    static template = "web.KanbanImage";
    static props = {
        ...standardWidgetProps,
        imgFieldName: { type: String },
        innerImgField: { type: String, optional: true },
        imgClass: { type: String, optional: true },
    };

    get mainImageSrc() {
        return this.getImageSrc();
    }
    get innerImageSrc() {
        return this.getImageSrc(this.props.innerImgField);
    }
    get hasInnerPic() {
        return this.props.record.data[this.props.innerImgField];
    }

    getImageSrc(fieldName) {
        const record = this.props.record;
        const value = fieldName ? this.props.record.data[fieldName][0] : record.resId;
        return getImageSrcFromRecordInfo(record, record.resModel, this.props.imgFieldName, value); // todo placeholder
    }
}

export const kanbanImageWidget = {
    component: KanbanImage,
    fieldDependencies: [{ name: "write_date", type: "datetime" }],
    extractProps: ({ attrs, options }) => {
        return {
            imgFieldName: options.field,
            innerImgField: options.inner,
            imgClass: options.class,
            // alt: attrs.alt, // TODO
            // todo: placeholder
        };
    },
};

registry.category("view_widgets").add("kanban_image", kanbanImageWidget);
