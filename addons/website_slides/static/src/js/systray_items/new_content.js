/** @odoo-module **/

import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from 'web.utils';

patch(NewContentModal.prototype, 'website_slides_new_content', {
    setup() {
        this._super();

        const newSlidesChannelElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_slides');
        newSlidesChannelElement.createNewContent = () => this.onAddContent('website_slides.slide_channel_action_add');
        newSlidesChannelElement.status = MODULE_STATUS.INSTALLED;
    },
    /**
     * @override
     */
    async onWillStart() {
        await this._super(...arguments);
        this.isSlideManager = await this.user.hasGroup('website_slides.group_website_slides_officer');
        if (this.isSlideManager) {
            this.state.newContentElements = this.state.newContentElements.map(element => {
                if (element.moduleXmlId === 'base.module_website_slides') {
                    element.isDisplayed = true;
                }
                return element;
            });
        }
    },
});
