import { useHover } from "@mail/utils/common/hooks";
import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSearch extends Component {
    static template = "mail.DiscussSearch";
    static props = ["class?"];
    static components = { Dropdown };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.command = useService("command");
        this.ui = useService("ui");
        this.searchHover = useHover(["search-btn", "search-floating"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.searchFloating.isOpen = true;
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.searchFloating.isOpen = false;
                }
            },
        });
        this.searchFloating = useDropdownState();
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

    onClickSearchConversations() {
        this.command.openMainPalette({ searchValue: "@" });
    }
}
