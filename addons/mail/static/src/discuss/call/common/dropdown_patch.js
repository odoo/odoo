import { Dropdown } from "@web/core/dropdown/dropdown";
import { patch } from "@web/core/utils/patch";

Object.assign(Dropdown.props, {
    openOnMouseEnter: {
        type: Boolean,
        optional: true,
    },
});
Object.assign(Dropdown.defaultProps, {
    openOnMouseEnter: true,
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
