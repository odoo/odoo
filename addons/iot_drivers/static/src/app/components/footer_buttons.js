/* global owl */

import useStore from "../hooks/store_hook.js";
import { CredentialsDialog } from "./dialog/credentials_dialog.js";
import { HandlerDialog } from "./dialog/handlers_dialog.js";
import { DebuggingToolsDialog } from "./dialog/debugging_tools_dialog.js";
import { TimeDialog } from "./dialog/time_dialog.js";

const { Component, xml } = owl;

export class FooterButtons extends Component {
    static props = {};
    static components = {
        DebuggingToolsDialog,
        HandlerDialog,
        CredentialsDialog,
        TimeDialog,
    };

    setup() {
        this.store = useStore();
    }

    static template = xml`
    <div class="w-100 d-flex flex-wrap align-items-cente gap-2 justify-content-center" t-translation="off">
        <a t-if="store.isLinux and !store.base.is_access_point_up" class="btn btn-primary btn-sm" href="/status" target="_blank">
            Status Display
        </a>
        <a t-if="store.isLinux and !store.base.is_access_point_up" class="btn btn-primary btn-sm" t-att-href="'http://' + this.store.base.ip + ':631'" target="_blank">
            Printer Server
        </a>
        <DebuggingToolsDialog t-if="this.store.advanced and this.store.isLinux" />
        <CredentialsDialog t-if="this.store.advanced" />
        <HandlerDialog t-if="this.store.advanced" />
        <a t-if="this.store.advanced" class="btn btn-primary btn-sm" href="/logs" target="_blank">View Logs</a>
        <TimeDialog/>
    </div>
  `;
}
