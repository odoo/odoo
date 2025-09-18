// @ts-check

/** @module @web/components/file_upload/file_upload_progress_container - Container that renders progress indicators for all active file uploads */

import { Component } from "@odoo/owl";

export class FileUploadProgressContainer extends Component {
    static template = "web.FileUploadProgressContainer";
    static props = {
        Component: { optional: false },
        shouldDisplay: { type: Function, optional: true },
        fileUploads: { type: Object },
    };
}
