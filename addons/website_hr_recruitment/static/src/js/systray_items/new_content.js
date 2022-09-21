/** @odoo-module **/

import { NewContentModal, MODULE_STATUS } from '@website/systray_items/new_content';
import { patch } from 'web.utils';

patch(NewContentModal.prototype, 'website_hr_recruitment_new_content', {
    setup() {
        this._super();

        const newJobElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_hr_recruitment');
        newJobElement.createNewContent = () => this.createNewJob();
        newJobElement.status = MODULE_STATUS.INSTALLED;
    },

    async createNewJob() {
        const url = await this.rpc('/jobs/add');
        this.website.goToWebsite({ path: url, edition: true });
        this.websiteContext.showNewContentModal = false;
    }
});
