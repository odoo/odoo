/** @odoo-module */

import { unpatchAvatarCardPopover } from "@hr/components/avatar_card/avatar_card_popover_patch";
import { unpatchAvatarCardResourcePopover } from "@hr/components/avatar_card_resource/avatar_card_resource_popover_patch";

unpatchAvatarCardPopover();
unpatchAvatarCardResourcePopover();
