import { Avatar } from "@mail/views/web/fields/avatar/avatar";
import { AvatarCardResourcePopover } from "../avatar_card_resource/avatar_card_resource_popover";

export class AvatarResource extends Avatar {
    static components = { ...super.components, Popover: AvatarCardResourcePopover };
}
