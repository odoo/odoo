/* @odoo-module */

import { loader } from "@web/core/emoji_picker/emoji_picker";

import { loadJS } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(loader, {
    loadEmoji: () => loadJS(`${session.origin}/im_livechat/emoji_bundle`),
});
