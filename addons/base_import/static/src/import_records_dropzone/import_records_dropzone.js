import { Component } from "@odoo/owl";
import { Dropzone } from "@web/core/dropzone/dropzone";

export class ImportRecordsDropzone extends Component {
    static template = "base_import.ImportRecordsDropzone";
    static components = { Dropzone };
    static props = { onDrop: Function, ref: Object, resModel: String };

    /** @returns {Object} */
    get dropzoneProps() {
        return {
            ref: this.props.ref,
            onDrop: this.props.onDrop,
        };
    }
}
