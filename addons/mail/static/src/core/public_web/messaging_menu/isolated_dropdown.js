import { Dropdown } from "@web/core/dropdown/dropdown";

/** Never a submenu of an ancestor Dropdown it's embedded in, even visually/positionally. */
export class IsolatedDropdown extends Dropdown {
    get hasParent() {
        return false;
    }
}
