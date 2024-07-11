/** @odoo-module **/
import { SwitchCompanyMenu, SwitchCompanyItem } from "@web/webclient/switch_company_menu/switch_company_menu";

export class MobileSwitchCompanyItem extends SwitchCompanyItem {}
MobileSwitchCompanyItem.components = {...SwitchCompanyItem, MobileSwitchCompanyItem}
MobileSwitchCompanyItem.template = "web.MobileSwitchCompanyItem";
export class MobileSwitchCompanyMenu extends SwitchCompanyMenu {}
MobileSwitchCompanyMenu.template = "web.MobileSwitchCompanyMenu";
MobileSwitchCompanyMenu.components = {...SwitchCompanyMenu, MobileSwitchCompanyItem}
