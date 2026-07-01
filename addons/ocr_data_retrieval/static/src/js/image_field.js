/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ImageField } from "@web/views/fields/image/image_field";

patch(ImageField.prototype, "ImagefieldPatch",{
    getUrl(previewFieldName) {
        if (!this.props.value){
            return `/ocr_data_retrieval/static/src/img/pdf.png`
        }
        return this._super(...arguments)
    }
})
