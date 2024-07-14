/** @odoo-module **/

import { ControlPanel } from "@web/search/control_panel/control_panel";
import { SearchBar } from "@web/search/search_bar/search_bar";
import { SearchBarMenu } from "@web/search/search_bar_menu/search_bar_menu";
import { useBus } from "@web/core/utils/hooks";
import { GroupMenu } from "./group_menu";


export class MrpMpsControlPanel extends ControlPanel {
    setup() {
        super.setup();
        useBus(this.env.searchModel, "update", () => {
            this.env.config.offset = 0;
            this.env.config.limit = this.env.defaultPageLimit;
            this.env.model.load(this.env.searchModel.domain, this.env.config.offset, this.env.config.limit);
        });
    }
}

export class MrpMpsSearchBarMenu extends SearchBarMenu {
    static template = "mrp_mps.SearchBarMenu";
    static components = { ...SearchBarMenu.components, GroupMenu };
}

export class MrpMpsSearchBar extends SearchBar {
    static template = "mrp_mps.SearchBar";
    static components = { ...SearchBar.components, MrpMpsSearchBarMenu };
}
