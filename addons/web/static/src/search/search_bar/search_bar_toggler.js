import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    usePlugin,
    proxy,
    t,
    useProps,
} from "@odoo/owl";
import { OfflinePlugin } from "@web/core/offline/offline_plugin";
import { useSetupAction } from "@web/search/action_hook";
import { useEnv } from "@web/owl2/utils";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class SearchBarToggler extends Component {
    static template = "web.SearchBar.Toggler";
    props = useProps({
        isSmall: t.boolean(),
        showSearchBar: t.boolean(),
        toggleSearchBar: t.function(),
    });
}

export class OfflineSearchBarToggler extends SearchBarToggler {
    static template = "web.SearchBar.Toggler.Offline";
    setup() {
        const offlinePlugin = usePlugin(OfflinePlugin);
        onWillStart(async () => {
            const { actionId, viewType } = this.env.config;
            const availableSearches = await offlinePlugin.getAvailableSearches(actionId, viewType);
            this.isDisabled = Object.keys(availableSearches).length <= 1;
        });
    }
}

export function useSearchBarToggler() {
    const ui = useService("ui");
    const env = useEnv();
    const props = useProps();

    // keep the toggle state when switching between views of the same action,
    // otherwise display the search bar by default when there are active search
    // items (default filters, search values, ...), even on small screens
    let isToggled = props.globalState?.searchBarToggled ?? Boolean(env.searchModel?.query?.length);
    useSetupAction({
        getGlobalState: () => ({ searchBarToggled: isToggled }),
    });
    const state = proxy({
        isSmall: ui.isSmall,
        showSearchBar: false,
        manuallyToggled: false,
    });
    const updateState = () => {
        state.isSmall = ui.isSmall;
        state.showSearchBar = !ui.isSmall || isToggled;
    };
    updateState();

    function toggleSearchBar() {
        isToggled = !isToggled;
        state.manuallyToggled = true;
        updateState();
    }

    const onResize = useDebounced(updateState, 200);
    onMounted(() => {
        browser.addEventListener("resize", onResize);
    });
    onWillUnmount(() => browser.removeEventListener("resize", onResize));

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
