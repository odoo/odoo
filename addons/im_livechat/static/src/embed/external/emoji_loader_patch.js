/* @odoo-module */

import { loader } from "@mail/core/common/emoji_picker";

import { loadBundle } from "@web/core/assets";
import { memoize } from "@web/core/utils/functions";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(loader, "im_livechat/emoji_loader", {
    loadEmoji: memoize(() =>
        loadBundle({
            jsLibs: [`${session.origin}/im_livechat/emoji_bundle`],
        })
    ),
});
