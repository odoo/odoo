import { patch } from "@web/core/utils/patch";
import {
    LeadGenerationDropdown,
    MODULE_STATUS
} from "@crm/components/lead_generation_dropdown/lead_generation_dropdown";
import { useService } from "@web/core/utils/hooks";
import { AddPageDialog } from "@website/components/dialog/add_page_dialog";

patch(LeadGenerationDropdown.prototype, {
    setup() {
        super.setup();
        this.website = useService('website');
        const websiteElement = this.state.dropdownContentElements.find(element => element.moduleXmlId === 'base.module_website');
        Object.assign(websiteElement, {
            onClick: () => this.createLandingPage(),
            status: MODULE_STATUS.INSTALLED,
            model: 'website'
        });
    },
    async createLandingPage() {
        await this.website.goToWebsite({ path: '/' });
        this.dialogs.add(AddPageDialog, { websiteId: this.website.currentWebsite.id, defaultTemplateId: 'landing' });
    }
});
