import {
    NewContentSystrayItem,
    MODULE_STATUS,
} from "@website/client_actions/website_preview/new_content_systray_item";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

patch(NewContentSystrayItem.prototype, {
    setup() {
        super.setup();

        const newJobElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_hr_recruitment');
        newJobElement.createNewContent = () => this.createNewJob();
        newJobElement.status = MODULE_STATUS.INSTALLED;
        newJobElement.model = 'hr.job';
    },

    async createNewJob() {
        const url = await rpc('/jobs/add');
        this.website.goToWebsite({ path: url, edition: true });
    },
});
