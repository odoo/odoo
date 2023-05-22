/** @odoo-module */

import { unpatch } from "@web/core/utils/patch";
import { AvatarCardPopover } from "@mail/discuss/web/avatar_card/avatar_card_popover";

unpatch(AvatarCardPopover.prototype, "hr");
