/* global Fuse */
/* Copyright 2023 Taras Shabaranskyi
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {AppsMenuCanonicalSearchBar} from "@web_responsive/components/menu_canonical_searchbar/searchbar.esm";

/**
 * @extends AppsMenuCanonicalSearchBar
 */
export class AppsMenuFuseSearchBar extends AppsMenuCanonicalSearchBar {
    setup() {
        super.setup();
        this.fuseOptions = {
            keys: ["displayName"],
            threshold: 0.43,
        };
        this.rootMenuItems = new Fuse(this.getRootMenuItems(), this.fuseOptions);
        this.subMenuItems = new Fuse(this.getSubMenuItems(), this.fuseOptions);
    }

    _searchMenus() {
        const {state} = this;
        const query = this.inputValue;
        state.hasResults = query !== "";
        state.rootItems = this.rootMenuItems.search(query);
        state.subItems = this.subMenuItems.search(query);
    }
}

AppsMenuFuseSearchBar.props = {};
AppsMenuFuseSearchBar.template = "web_responsive.AppsMenuFuseSearchBar";
