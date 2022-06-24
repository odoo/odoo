/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { ImageSelector } from '@web_editor/components/media_dialog/image_selector';

patch(ImageSelector.prototype, 'media_dialog_website', {
    get attachmentsDomain() {
        const domain = this._super();
        domain.push('|', ['url', '=', false], '!', ['url', '=like', '/web/image/website.%']);
        domain.push(['key', '=', false]);
        return domain;
    }
});
