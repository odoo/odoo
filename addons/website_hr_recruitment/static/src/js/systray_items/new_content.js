import {
    NewContentSystrayItem,
    MODULE_STATUS,
} from "@website/client_actions/website_preview/new_content_systray_item";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(NewContentSystrayItem.prototype, {
    setup() {
        super.setup();

        const newJobElement = this.state.newContentElements.find(element => element.moduleXmlId === 'base.module_website_hr_recruitment');
        newJobElement.createNewContent = () => this.createNewJob();
        newJobElement.status = MODULE_STATUS.INSTALLED;
        newJobElement.model = 'hr.job';
    },

    canCreateJobOnCurrentWebsite() {
        const websiteCompanyId = this.website.currentWebsite.company_id;
        if (!websiteCompanyId || user.activeCompanies.some((c) => c.id === websiteCompanyId)) {
            return true;
        }
        const websiteCompany = user.allowedCompanies.find((c) => c.id === websiteCompanyId);
        this.dialogs.add(AlertDialog, {
            title: _t("Company Mismatch"),
            body: websiteCompany
                ? _t("This website belongs to %(company)s, which isn't one of your active companies. Switch to it first, then try again.", { company: websiteCompany.name })
                : _t("This website belongs to a company you don't have access to. Ask your administrator for access before creating a Job Position here."),
        });
        return false;
    },

    async createNewJob() {
        if (!this.canCreateJobOnCurrentWebsite()) {
            return;
        }
        const url = await rpc('/jobs/add');
        this.website.goToWebsite({ path: url, edition: true });
    },
});
