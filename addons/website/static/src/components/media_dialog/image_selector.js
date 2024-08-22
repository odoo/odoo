/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ImageSelector } from '@web_editor/components/media_dialog/image_selector';
import { ImageSelector as HtmlImageSelector } from "@html_editor/main/media/media_dialog/image_selector";

patch(ImageSelector.prototype, {
});

patch(HtmlImageSelector.prototype, {
});
