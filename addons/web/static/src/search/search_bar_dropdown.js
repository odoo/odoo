import { props, types as t } from "@odoo/owl";
import { Dropdown, dropdownProps } from "@web/core/dropdown/dropdown";

export class SearchBarDropdown extends Dropdown {
    props = props({
        ...dropdownProps,
        popoverWillCloseOnClickAway: t.function(),
    });

    popoverCloseOnClickAway(target) {
        return (
            this.props.popoverWillCloseOnClickAway(target) && super.popoverCloseOnClickAway(target)
        );
    }
}
