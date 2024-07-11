/** @odoo-module **/

import { Component, useEffect, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class SearchBarToggler extends Component {}
SearchBarToggler.template = "web.SearchBar.Toggler";
SearchBarToggler.props = {
    isSmall: Boolean,
    showSearchBar: Boolean,
    toggleSearchBar: Function,
};

export function useSearchBarToggler() {
    const ui = useService("ui");

    let isToggled = false;
    const state = useState({
        isSmall: ui.isSmall,
        showSearchBar: false,
    });
    const updateState = () => {
        state.isSmall = ui.isSmall;
        state.showSearchBar = !ui.isSmall || isToggled;
    };
    updateState();

    function toggleSearchBar() {
        isToggled = !isToggled;
        updateState();
    }

    const onResize = useDebounced(updateState, 200);
    useEffect(
        () => {
            browser.addEventListener("resize", onResize);
            return () => browser.removeEventListener("resize", onResize);
        },
        () => []
    );

    return {
        state,
        component: SearchBarToggler,
        get props() {
            return {
                isSmall: state.isSmall,
                showSearchBar: state.showSearchBar,
                toggleSearchBar,
            };
        },
    };
}
