/* Copyright 2018 Tecnativa - Jairo Llopis
 * Copyright 2021 ITerra - Sergey Shebanin
 * Copyright 2023 Onestein - Anjeel Haria
 * Copyright 2023 Taras Shabaranskyi
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {Component, useState} from "@odoo/owl";
import {useAutofocus, useService} from "@web/core/utils/hooks";

/**
 * @extends Component
 * @property {{el: HTMLInputElement}} searchBarInput
 */
export class AppsMenuOdooSearchBar extends Component {
    setup() {
        super.setup();
        this.state = useState({
            rootItems: [],
            subItems: [],
            offset: 0,
            hasResults: false,
        });
        this.searchBarInput = useAutofocus({refName: "SearchBarInput"});
        this.command = useService("command");
    }

    /**
     * @returns {String}
     */
    get inputValue() {
        const {el} = this.searchBarInput;
        return el ? el.value : "";
    }

    set inputValue(value) {
        const {el} = this.searchBarInput;
        if (el) {
            el.value = value;
        }
    }

    _onSearchInput() {
        if (this.inputValue) {
            this._openSearchMenu(this.inputValue);
            this.inputValue = "";
        }
    }

    _onSearchClick() {
        this._openSearchMenu();
    }

    /**
     * @param {String} [value]
     * @private
     */
    _openSearchMenu(value) {
        const searchValue = value ? `/${value}` : "/";
        this.command.openMainPalette({searchValue}, null);
    }
}

AppsMenuOdooSearchBar.props = {};
AppsMenuOdooSearchBar.template = "web_responsive.AppsMenuOdooSearchBar";
