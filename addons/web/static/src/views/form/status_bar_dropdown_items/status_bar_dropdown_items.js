import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { StatusBarButtons } from "../status_bar_buttons/status_bar_buttons";

export class StatusBarDropdownItems extends StatusBarButtons {
    static template = "web.StatusBarDropdownItems";
    static components = {
        DropdownItem,
    };
}
