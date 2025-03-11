import { Component } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { SearchInputPopover } from "@mail/discuss/core/common/search_input_popover";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class SearchInput extends Component {
    static template = "discuss.SearchInput";
    static components = {};
    static props = [];
    static defaultProps = {};

    setup() {
        this.popover = usePopover(SearchInputPopover, {
            position: "bottom-start"
        });
    }

    openPopover(ev) {
        const target = ev.currentTarget;
        if (!this.popover.isOpen) {
            this.popover.open(target);
        }
    }
}
