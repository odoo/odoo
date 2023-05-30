/** @odoo-module */

import { loader } from "@mail/emoji_picker/emoji_picker";

import { loadBundle } from "@web/core/assets";
import { patch } from "@web/core/utils/patch";
import { memoize } from "@web/core/utils/functions";
import { session } from "@web/session";

patch(loader, "im_livechat/emoji_loader", {
    loadEmoji: memoize(() =>
        loadBundle({
            jsLibs: [`${session.origin}/im_livechat/emoji_bundle`],
        })
    ),
});
