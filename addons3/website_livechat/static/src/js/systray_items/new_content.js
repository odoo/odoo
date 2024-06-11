/** @odoo-module **/

import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from "@web/core/utils/patch";

patch(NewContentModal.prototype, {
    setup() {
        super.setup();

        const newChannelElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_livechat');
        newChannelElement.createNewContent = () => this.onAddContent('website_livechat.im_livechat_channel_action_add');
        newChannelElement.status = MODULE_STATUS.INSTALLED;
        newChannelElement.model = 'im_livechat.channel';
    },
});
