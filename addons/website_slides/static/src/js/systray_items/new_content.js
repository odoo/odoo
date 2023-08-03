/** @odoo-module **/

import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from "@web/core/utils/patch";

patch(NewContentModal.prototype, {
    setup() {
        super.setup();

        const newSlidesChannelElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_slides');
        newSlidesChannelElement.createNewContent = () => this.onAddContent('website_slides.slide_channel_action_add');
        newSlidesChannelElement.status = MODULE_STATUS.INSTALLED;
        newSlidesChannelElement.model = 'slide.channel';
    },
});
