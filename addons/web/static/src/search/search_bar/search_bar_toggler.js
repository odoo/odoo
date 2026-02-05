import { useLayoutEffect } from "@web/owl2/utils";
import { Component, onWillStart, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class SearchBarToggler extends Component {
    static template = "web.SearchBar.Toggler";
    static props = {
        isSmall: Boolean,
        showSearchBar: Boolean,
        toggleSearchBar: Function,
    };
}

export class OfflineSearchBarToggler extends SearchBarToggler {
    static template = "web.SearchBar.Toggler.Offline";
    setup() {
        const offlineService = useService("offline");
        onWillStart(async () => {
            const { actionId, viewType } = this.env.config;
            const availableSearches = await offlineService.getAvailableSearches(actionId, viewType);
            this.isDisabled = Object.keys(availableSearches).length <= 1;
        });
    }
}

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
    useLayoutEffect(
        () => {
            browser.addEventListener("resize", onResize);
            return () => browser.removeEventListener("resize", onResize);
        },
        () => []
    );

    return {
        state,
        component: SearchBarToggler,
        offlineComponent: OfflineSearchBarToggler,
        get props() {
            return {
                isSmall: state.isSmall,
                showSearchBar: state.showSearchBar,
                toggleSearchBar,
            };
        },
    };
}
