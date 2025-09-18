// @ts-check

/** @module @web/search/search_bar/search_bar_toggler - Toggle button and hook for responsive search bar visibility on small screens */

import { Component, useEffect, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
/** Toggle button for showing/hiding the search bar on small screens. */
export class SearchBarToggler extends Component {
    static template = "web.SearchBar.Toggler";
    static props = {
        isSmall: Boolean,
        showSearchBar: Boolean,
        toggleSearchBar: Function,
    };
}

/**
 * OWL hook that manages responsive search bar visibility.
 * Automatically shows the search bar on large screens and provides
 * a toggle function for small screens.
 * @returns {{ state: { isSmall: boolean, showSearchBar: boolean }, component: typeof SearchBarToggler, props: Object }}
 */
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
        () => [],
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
