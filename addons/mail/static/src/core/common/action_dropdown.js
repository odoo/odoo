import { ActionButton } from "@mail/core/common/action_button";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

/**
 * Same chrome as {@link ActionButton}, rendered as a `DropdownItem` instead
 * of a plain `<button>`, for an action shown inside another dropdown's menu
 * (@see props.dropdown).
 */
export class ActionDropdown extends ActionButton {
    static template = "mail.ActionDropdown";
    static components = { DropdownItem };
}
