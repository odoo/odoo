/** @odoo-module **/

import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from "@web/core/utils/patch";

patch(NewContentModal.prototype, {
    setup() {
        super.setup();

        const newEventElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_event');
        newEventElement.createNewContent = () => this.onAddContent('website_event.event_event_action_add', true);
        newEventElement.status = MODULE_STATUS.INSTALLED;
        newEventElement.model = 'event.event';
    },
});
