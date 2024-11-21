import { SwitchCompanyMenu } from "@web/webclient/switch_company_menu/switch_company_menu";

export class MobileSwitchCompanyMenu extends SwitchCompanyMenu {
    static template = "web.MobileSwitchCompanyMenu";

    setup() {
        super.setup();
        this.state.isOpen = false;
    }

    get show() {
        return !this.hasLotsOfCompanies || this.state.isOpen === true;
    }

    toggleCollapsible() {
        if (this.hasLotsOfCompanies) {
            this.state.isOpen = !this.state.isOpen;
        }
    }
}
