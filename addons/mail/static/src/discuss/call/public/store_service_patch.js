import { Store } from "@mail/core/common/store_plugin";
import { patchModel } from "@mail/model/export";

import { location } from "@web/core/browser/browser";

export const StorePatch = patchModel(Store, {
    _hasFullscreenUrlOnUpdate() {
        const channel = this.discuss?.thread?.channel;
        let base = location.href;
        if (this._hasFullscreenUrl && channel?.invitationLink) {
            // Mirror the meeting link so that it can be copied from the address bar.
            base = channel.invitationLink;
        } else if (channel) {
            base = `/discuss/channel/${channel.id}`;
        }
        const url = new URL(base, location.origin);
        url.search = location.search;
        url.searchParams.delete("fullscreen");
        window.history.replaceState(window.history.state, null, url);
    },
});
