import { ActionDropdown } from "@mail/core/common/action_dropdown";

/**
 * ActionDropdown variant for call-related actions, set as an action's `dropdownComponent`.
 * Restores, for the dropdown-item rendering of a call action, the circular icon-background
 * styling previously carried by `o-tag-JOIN_LEAVE_CALL` (@see action_call_dropdown.scss).
 */
export class ActionCallDropdown extends ActionDropdown {
    static template = "discuss.ActionCallDropdown";

    get btnRootClass() {
        return "o-mail-ActionCallDropdown";
    }
}
