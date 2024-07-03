import { Discuss } from "@mail/core/public_web/discuss";
import { WelcomePage } from "@mail/discuss/core/public/welcome_page";

import { Component, useEffect, useState } from "@odoo/owl";

import { useService } from "@web/core/utils/hooks";

export class DiscussPublic extends Component {
    static components = { Discuss, WelcomePage };
    static props = [];
    static template = "mail.DiscussPublic";

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.state = useState({
            welcome:
                this.store.shouldDisplayWelcomeViewInitially ||
                this.store.discuss_public_thread.defaultDisplayMode === "video_full_screen",
        });
        useEffect(
            (welcome) => {
                if (!welcome) {
                    this.displayChannel();
                }
            },
            () => [this.state.welcome]
        );
        if (this.store.isChannelTokenSecret) {
            // Change the URL to avoid leaking the invitation link.
            window.history.replaceState(
                window.history.state,
                null,
                `/discuss/channel/${this.store.discuss_public_thread.id}${window.location.search}`
            );
        }
    }

    displayChannel() {
        this.store.discuss_public_thread.setAsDiscussThread(false);
        this.store.discuss_public_thread.fetchChannelMembers();
    }
}
