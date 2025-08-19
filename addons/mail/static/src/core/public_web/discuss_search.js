import { useHover } from "@mail/utils/common/hooks";
import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { _t } from "@web/core/l10n/translation";
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
        });
        this.searchFloating = useDropdownState();
        this.meetingFloating = useDropdownState();
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

    get newMeetingText() {
        return _t("New Meeting");
    }

    onClickNewMeeting() {
        this.store.startMeeting();
        if (this.env.inMessagingMenu) {
            this.env.inMessagingMenu.dropdown.close();
        }
    }

    onClickSearchConversations() {
        this.command.openMainPalette({ searchValue: "@" });
    }
}
