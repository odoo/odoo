import {_t} from "@web/core/l10n/translation";
import { ActionMenus } from "@web/search/action_menus/action_menus";
import { CogMenuMixin } from "@web/search/cog_menu/cog_menu";


export class AccountActionMenus extends ActionMenus {

    actionMenuTitle() {
        return _t("Download");
    }

    async getPrintItems() {
        const printItems = await super.getPrintItems();
        if (this.props?.getActiveIds && this.props?.resModel === "account.move") {
            const extraPrintItems = await this.orm.call("account.move", "get_extra_print_items", [this.props.getActiveIds()]);
            return [...extraPrintItems, ...printItems];
        }
        return printItems;
    }

}


export class AccountCogMenu extends CogMenuMixin(AccountActionMenus) {}
