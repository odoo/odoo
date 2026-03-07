/* Copyright 2023 Taras Shabaranskyi
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {AppsMenuCanonicalSearchBar} from "@web_responsive/components/menu_canonical_searchbar/searchbar.esm";
import {AppsMenuFuseSearchBar} from "@web_responsive/components/menu_fuse_searchbar/searchbar.esm";
import {AppsMenuOdooSearchBar} from "@web_responsive/components/menu_odoo_searchbar/searchbar.esm";
import {Component} from "@odoo/owl";
import {session} from "@web/session";

export class AppsMenuSearchBar extends Component {
    setup() {
        super.setup();
        this.searchType = session.apps_menu.search_type || "canonical";
    }
}

Object.assign(AppsMenuSearchBar, {
    props: {},
    template: "web_responsive.AppsMenuSearchBar",
    components: {
        AppsMenuOdooSearchBar,
        AppsMenuCanonicalSearchBar,
        AppsMenuFuseSearchBar,
    },
});
