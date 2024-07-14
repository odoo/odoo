/* @odoo-module */

import { FileViewer } from "@web/core/file_viewer/file_viewer";
import { patch } from "@web/core/utils/patch";

import { useBackButton } from "@web_mobile/js/core/hooks";

patch(FileViewer.prototype, {
    setup() {
        super.setup();
        useBackButton(() => this.close());
    },
});
