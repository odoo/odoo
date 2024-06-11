/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ImageSelector } from '@web_editor/components/media_dialog/image_selector';

patch(ImageSelector.prototype, {
    get attachmentsDomain() {
        const domain = super.attachmentsDomain;
        domain.push('|', ['url', '=', false], '!', ['url', '=like', '/web/image/website.%']);
        domain.push(['key', '=', false]);
        return domain;
    }
});
