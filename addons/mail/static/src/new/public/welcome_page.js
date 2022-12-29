/* @odoo-module */

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useMessaging, useStore } from "../core/messaging_hook";

export class WelcomePage extends Component {
    static props = ["data?", "proceed?"];
    static template = "mail.welcome_page";

    setup() {
        this.messaging = useMessaging();
        this.store = useStore();
        this.rpc = useService("rpc");
        /** @type {import('@mail/new/core/persona_service').PersonaService} */
        this.personaService = useService("mail.persona");
        this.state = useState({
            userName: "Guest",
        });
    }

    onKeydownInput(ev) {
        if (ev.key === "Enter") {
            this.joinChannel();
        }
    }

    async joinChannel() {
        if (this.store.guest) {
            await this.personaService.updateGuestName(this.store.self, this.state.userName.trim());
        }
        if (this.props.data?.discussPublicViewData.addGuestAsMemberOnJoin) {
            await this.rpc("/mail/channel/add_guest_as_member", {
                channel_id: this.props.data.channelData.id,
                channel_uuid: this.props.data.channelData.uuid,
            });
        }
        this.props.proceed?.();
    }
}
