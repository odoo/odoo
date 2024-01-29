import {
    SwitchCompanyMenu,
    SwitchCompanyItem,
} from "@web/webclient/switch_company_menu/switch_company_menu";

export class MobileSwitchCompanyItem extends SwitchCompanyItem {
    static template = "web.MobileSwitchCompanyItem";
    static components = { ...SwitchCompanyItem, MobileSwitchCompanyItem };
}
export class MobileSwitchCompanyMenu extends SwitchCompanyMenu {
    static template = "web.MobileSwitchCompanyMenu";
    static components = { ...SwitchCompanyMenu, MobileSwitchCompanyItem };
}
