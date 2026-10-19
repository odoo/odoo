import { SearchInput } from "@mail/core/common/search_input";
import { propSignal, useSearch } from "@mail/utils/common/hooks";
import { Component, signal, types, useEffect, useProps } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { useService } from "@web/core/utils/hooks";

export class DiscussSearch extends Component {
    static template = "mail.DiscussSearch";
    static components = { SearchInput };

    searchInput = signal.ref();

    setup() {
        this.store = useService("mail.store");
        this.autofocus = propSignal("autofocus", types.number(), { optional: true });
        this.messagingMenuUiState = propSignal(
            "messagingMenuUiState",
            types.instanceOf(this.store.MessagingMenuUIState)
        );
        this.props = useProps({
            class: types.or([types.string(), types.object()]).optional(),
        });
<<<<<<< 3a00e0b2160c3572853fa3f8b289ce7f1d7bb159
        this.search = useSearch({
            searchTerm: this.messagingMenuUiState()._.fieldsAttrSignal.get("searchTerm"),
        });
        useEffect(() => {
            if (this.autofocus?.()) {
                this.searchInput()?.focus();
            }
||||||| a862c87e3268d61753353838da6a011c22ca74f2
        this.meetingHover = useHover(["meeting-btn", "meeting-floating"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.meetingFloating.isOpen = true;
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.meetingFloating.isOpen = false;
                }
            },
=======
        this.meetingHover = useHover(["meeting-btn"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.meetingFloating.isOpen = true;
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.meetingFloating.isOpen = false;
                }
            },
>>>>>>> 1c12bf434df27c02659b6398f36fdf9fa6ffb201
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
