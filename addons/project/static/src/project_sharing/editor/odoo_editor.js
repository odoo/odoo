/** @odoo-module **/

import { OdooEditor } from "@web_editor/js/editor/odoo-editor/src/OdooEditor";
import { patch } from "@web/core/utils/patch";

/**
 * The goal of this patch is to remove the crop and replace buttons
 * from the image editor toolbar as the portal user doesn't have
 * access to save modified attachments.
 */
patch(OdooEditor.prototype, "project_sharing_portal_toolbar_media_update", {
    /**
     * @override
     */
    _updateToolbar(show) {
        this._super(show);
        const isInMedia = this.toolbar.classList.contains('oe-media');
        const cropButton = this.toolbar.querySelector('#image-crop');
        const replaceButton = this.toolbar.querySelector('#media-replace');
        cropButton?.classList.toggle('d-none', isInMedia);
        replaceButton?.classList.toggle('d-none', isInMedia);
    },
});
