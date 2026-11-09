import { SearchInput } from "@mail/core/common/search_input";
import { propStatic, usePropsPlus } from "@mail/utils/common/hooks";
import { SearchStatePlugin } from "@mail/utils/common/search_state_plugin";
import {
    Component,
    computed,
    providePlugins,
    signal,
    types,
    useEffect,
    usePlugin,
} from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { useService } from "@web/core/utils/hooks";

export class DiscussSearch extends Component {
    static template = "mail.DiscussSearch";
    static components = { SearchInput };

    searchInput = signal.ref();

    setup() {
        this.store = useService("mail.store");
        this.props = usePropsPlus({
            autofocus: propStatic(types.signal(types.number()).optional(() => signal(null))),
            class: types.or([types.string(), types.object()]).optional(),
            messagingMenuUiState: propStatic(
                types.signal(types.instanceOf(this.store.MessagingMenuUIState))
            ),
        });
        providePlugins([SearchStatePlugin], {
            searchTerm: computed(() => this.props.messagingMenuUiState().searchTerm, {
                set: (searchTerm) => (this.props.messagingMenuUiState().searchTerm = searchTerm),
            }),
        });
        this.search = usePlugin(SearchStatePlugin);
        useEffect(() => {
            if (this.props.autofocus()) {
                this.searchInput()?.focus();
            }
        });
    }

    get class() {
        if (typeof this.props.class === "object" && this.props.class !== null) {
            return Object.entries(this.props.class)
                .filter(([_, val]) => val)
                .map(([key, _]) => key)
                .join(" ");
        }
        return this.props.class;
    }

    onKeydownSearch(ev) {
        if (getActiveHotkey(ev) === "escape") {
            ev.stopPropagation();
            ev.preventDefault();
            this.onClearSearch();
        }
    }

    onClearSearch() {
        this.search.searchTerm = "";
    }
}
