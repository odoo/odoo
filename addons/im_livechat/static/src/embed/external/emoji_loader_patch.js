/* @odoo-module */

import { loader } from "@web/core/emoji_picker/emoji_picker";

import { loadJS } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";
import { url } from "@web/core/utils/urls";

patch(loader, {
    loadEmoji: () => loadJS(url("/im_livechat/emoji_bundle")),
});
