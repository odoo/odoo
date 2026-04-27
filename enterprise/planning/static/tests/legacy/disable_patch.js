/** @odoo-module */

import {
    unpatchM2oResourceFieldPlanning,
    unpatchKanbanM2oResourceFieldPlanning
} from "@planning/views/fields/many2one_avatar_resource/many2one_avatar_resource_field_patch";
import { unpatchAvatarCardResourcePopover } from "@planning/components/avatar_card_resource/avatar_card_resource_popover_patch";

unpatchM2oResourceFieldPlanning();
unpatchKanbanM2oResourceFieldPlanning();
unpatchAvatarCardResourcePopover();
