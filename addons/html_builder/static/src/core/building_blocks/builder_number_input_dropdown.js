import { dropdownProps, Dropdown } from "@web/core/dropdown/dropdown";
import { t, useProps } from "@odoo/owl";

export class BuilderInputNumberDropdown extends Dropdown {
    props = useProps({ ...dropdownProps, closeOnClickAway: t.function() });

    handleClick(event) {
        if (this.props.disabled) {
            return;
        }

        event.stopPropagation();
        if (this.state.isOpen && !this.hasParent && !event.target.matches("input")) {
            this.state.close();
        } else if (event.target.matches("input")) {
            this.state.open();
        }
    }

    popoverCloseOnClickAway(target) {
        return super.popoverCloseOnClickAway(target) || this.props.closeOnClickAway(target);
    }
}
