import { useProps } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { ActionBase } from "@mail/core/common/action_base";

export class ActionDropdown extends ActionBase {
    static template = "mail.ActionDropdown";
    static components = { DropdownItem };

    props = useProps(ActionBase.propsSchema);

    setup() {
        super.setup();
        this.ui = useService("ui");
    }

    get alignmentClass() {
        return {
            "text-start": !this.ui.isSmall,
        };
    }

    get paddingClass() {
        return {
            "px-3 py-2": this.ui.isSmall,
            "px-2 py-1": !this.ui.isSmall,
        };
    }

    get classObj() {
        return {
            ...super.classObj,
            ...this.alignmentClass,
            ...this.paddingClass,
        };
    }
}
