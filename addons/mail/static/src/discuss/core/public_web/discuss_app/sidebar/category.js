import { useHover } from "@mail/utils/common/hooks";
import { Component } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";

export class DiscussSidebarCategory extends Component {
    static template = "mail.DiscussSidebarCategory";
    static props = ["category"];
    static components = { Dropdown };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.discusscorePublicWebService = useService("discuss.core.public.web");
        this.hover = useHover(["root", "floating"], {
            onHover: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.onHover(true);
                }
            },
            onAway: () => {
                if (this.store.discuss.isSidebarCompact) {
                    this.onHover(false);
                }
            },
        });
        this.floating = useDropdownState();
    }

    onHover(hovering) {
        this.floating.isOpen = hovering;
    }

    /** @returns {import("models").DiscussAppCategory} */
    get category() {
        return this.props.category;
    }

    get actions() {
        return [];
    }

    toggle() {
        this.category.is_open = !this.category.is_open;
    }
}
