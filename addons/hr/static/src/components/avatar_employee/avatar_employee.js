import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { AvatarCardEmployeePopover } from "../avatar_card_employee/avatar_card_employee_popover";

export class AvatarEmployee extends Avatar {
    static components = { ...super.components, Popover: AvatarCardEmployeePopover };
}
