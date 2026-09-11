/** @odoo-module **/
import { isMobileOS } from "@web/core/browser/feature_detection";
import { registry } from "@web/core/registry";
import { FileUploader } from "@web/views/fields/file_handler";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { _lt } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { isBinarySize } from "@web/core/utils/binary";
const placeholder = "/web/static/img/placeholder.png";
const { DateTime } = luxon;
import { url } from "@web/core/utils/urls";
import rpc from 'web.rpc';
const { useRef } = owl;

export const fileTypeMagicWordMap = {
    "/": "jpg",
    R: "gif",
    i: "png",
    P: "svg+xml",
};

export function imageCacheKey(value) {
    if (value instanceof DateTime) {
        return value.ts;
    }
    return "";
}
var translation = require('web.translation');
var _t = translation._t;
import { Component, useState, onWillUpdateProps } from "@odoo/owl";

export class DragAndDropBinaryField extends Component {
    setup() {
        /* setting for widget  */
        this.notification = useService("notification");
        this.isMobile = isMobileOS();
        this.state = useState({
            isValid: true,
        });
        this.inputFile = useRef('inputFile')
        this.image_picker = useRef('image_picker')
        this.rawCacheKey = this.props.record.data.__last_update;
        onWillUpdateProps((nextProps) => {
            const { record } = this.props;
            const { record: nextRecord } = nextProps;
            if (record.resId !== nextRecord.resId || nextRecord.mode === "readonly") {
                this.rawCacheKey = nextRecord.data.__last_update;
            }
        });
    }
    get sizeStyle() {
        /* Styling the widget */
        let style = "";
        if (this.props.width) {
            style += `max-width: ${this.props.width}px;`;
        }
        if (this.props.height) {
            style += `max-height: ${this.props.height}px;`;
        }
        return style;
    }
    get hasTooltip() {
        /* Method for getting the tooltip */
        return this.props.enableZoom && this.props.readonly && this.props.value;
    }
    getUrl(previewFieldName) {
         /* Get image URL */
        if (this.state.isValid && this.props.value) {
            if (isBinarySize(this.props.value)) {
                if (!this.rawCacheKey) {
                    this.rawCacheKey = this.props.record.data.__last_update;
                }
                return url("/web/image", {
                    model: this.props.record.resModel,
                    id: this.props.record.resId,
                    field: previewFieldName,
                    unique: imageCacheKey(this.rawCacheKey),
                });
            } else {
                // Use magic-word technique for detecting image type
                const magic = fileTypeMagicWordMap[this.props.value[0]] || "png";
                return `data:image/${magic};base64,${this.props.value}`;
            }
        }
        return placeholder;
    }
    /* File Remove */
    onFileRemove() {
        this.state.isValid = true;
        this.props.update(false);
    }
    /* File Upload */
    onFileUploaded(info) {
        this.state.isValid = true;
        this.rawCacheKey = null;
        this.props.update(info.data);
    }
    /* File Load */
    onLoadFailed() {
        this.state.isValid = false;
        this.notification.add(this.env._t("Could not display the selected image"), {
            type: "danger",
        });
    }
    /* Upload Image to the field */
    onImageUpload(){
        let file =this.inputFile.el.defaultValue
        if (file == "")
        {
            image_picker.classList.add('d-none');
        }
        else{
           rpc.query({
                model: 'ir.attachment',
                method: 'action_save_drag_and_drop_image',
                args: [[], {'resModel': this.props.record.resModel,
                'id': this.props.record.data.id, 'name': this.props.name}, file],
            }).then(function(results){
                location.reload();
            })

        }
    }
    /* method for dragging */
    onFileDragImage(){
        var image_picker = this.image_picker.el;
        image_picker.classList.remove('d-none');
    }
}

DragAndDropBinaryField.components = {
    FileUploader,
};
DragAndDropBinaryField.props = {
    ...standardFieldProps,
    enableZoom: { type: Boolean, optional: true },
    zoomDelay: { type: Number, optional: true },
    previewImage: { type: String, optional: true },
    acceptedFileExtensions: { type: String, optional: true },
    width: { type: Number, optional: true },
    height: { type: Number, optional: true },
};
DragAndDropBinaryField.defaultProps = {
    acceptedFileExtensions: "image/*",
};

DragAndDropBinaryField.displayName = _lt("Image");
DragAndDropBinaryField.supportedTypes = ["binary"];

DragAndDropBinaryField.fieldDependencies = {
    __last_update: { type: "datetime" },
};

DragAndDropBinaryField.extractProps = ({ attrs }) => {
    return {
        enableZoom: attrs.options.zoom,
        zoomDelay: attrs.options.zoom_delay,
        previewImage: attrs.options.preview_image,
        acceptedFileExtensions: attrs.options.accepted_file_extensions,
        width:
            attrs.options.size && Boolean(attrs.options.size[0])
                ? attrs.options.size[0]
                : attrs.width,
        height:
            attrs.options.size && Boolean(attrs.options.size[1])
                ? attrs.options.size[1]
                : attrs.height,
    };
};
DragAndDropBinaryField.template = 'FieldDragAndDropBinary';
registry.category("fields").add("drag_and_drop", DragAndDropBinaryField);
