/** @odoo-module native */
import { Chatter } from "@mail/chatter/web_portal/chatter";
import { Component, onWillDestroy, useSubEnv, xml } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useBus, useService } from "@web/core/utils/hooks";
import { OverlayContainer } from "@web/ui/overlay/overlay_container";

const log = makeLogger("portal.chatter");

export class PortalChatter extends Component {
    static template = xml`
        <Chatter threadId="props.resId" threadModel="props.resModel" composer="props.composer" twoColumns="props.twoColumns"/>
        <div class="position-fixed" style="z-index:1030"><OverlayContainer overlays="overlayService.overlays" rootId="'chatterRoot'"/></div>
    `;
    static components = { Chatter, OverlayContainer };
    static props = ["resId", "resModel", "composer", "twoColumns", "displayRating"];

    setup() {
        useSubEnv({
            displayRating: this.props.displayRating,
            inFrontendPortalChatter: true,
        });
        this.overlayService = useService("overlay");
        this.store = useService("mail.store");
        useBus(this.env.bus, "reload_chatter_content", () =>
            this._reloadChatterContent(),
        );
        onWillDestroy(() => {
            this.destroyed = true;
        });
    }

    _reloadChatterContent() {
        this.reloadRequested = true;
        return (this.reloadPromise ||= Promise.resolve().then(() =>
            this._fetchChatterContent(),
        ));
    }

    async _fetchChatterContent() {
        try {
            const thread = this.store.Thread.get({
                id: this.props.resId,
                model: this.props.resModel,
            });
            // fetchMessages inserts into the store before returning: concurrent
            // requests cannot be made safe by only guarding the final assignment.
            while (this.reloadRequested && !this.destroyed) {
                this.reloadRequested = false;
                log.logic("reload messages");
                let messages;
                try {
                    messages = await thread.fetchMessages();
                } catch (error) {
                    if (this.destroyed) {
                        return;
                    }
                    if (!this.reloadRequested) {
                        throw error;
                    }
                    log.logic("failed fetch superseded by queued reload");
                    continue;
                }
                if (!this.destroyed) {
                    thread.messages = messages;
                }
            }
        } finally {
            this.reloadPromise = undefined;
        }
    }
}
