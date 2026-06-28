import { t } from "@odoo/owl";

import { Dropdown, dropdownProps } from "@web/core/dropdown/dropdown";
import { patch } from "@web/core/utils/patch";

Object.assign(dropdownProps, {
    openOnMouseEnter: t.boolean().optional(true),
});

patch(Dropdown.prototype, {
    handleMouseEnter() {
        if (!this.props.openOnMouseEnter) {
            return;
        }
        super.handleMouseEnter(...arguments);
    },
    handleClick(ev) {
        if (
            !this.props.openOnMouseEnter &&
            this.hasParent &&
            this.state.isOpen &&
            !this.props.disabled
        ) {
            this.state.close();
            ev.stopPropagation();
            return;
        }
        super.handleClick(...arguments);
    },
});
