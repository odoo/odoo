/* global owl */

import useStore from "../hooks/useStore.js";
import { CredentialDialog } from "./dialog/CredentialDialog.js";
import { HandlerDialog } from "./dialog/HandlerDialog.js";
import { RemoteDebugDialog } from "./dialog/RemoteDebugDialog.js";

const { Component, xml } = owl;

export class FooterButtons extends Component {
    static props = {};
    static components = {
        RemoteDebugDialog,
        HandlerDialog,
        CredentialDialog,
    };

    setup() {
        this.store = useStore();
    }

    static template = xml`
    <div class="w-100 d-flex flex-wrap align-items-cente gap-2 justify-content-center">
        <a t-if="this.store.isLinux" class="btn btn-primary btn-sm" t-att-href="'http://' + this.store.base.ip + '/status'" target="_blank">Status Display</a>
        <a t-if="this.store.isLinux" class="btn btn-primary btn-sm" t-att-href="'http://' + this.store.base.ip + ':631'" target="_blank">Printer Server</a>
        <RemoteDebugDialog t-if="this.store.advanced and this.store.isLinux" />
        <CredentialDialog t-if="this.store.advanced" />
        <HandlerDialog t-if="this.store.advanced" />
        <a t-if="this.store.advanced" class="btn btn-primary btn-sm" t-att-href="'http://' + this.store.base.ip + '/logs'" target="_blank">View Logs</a>
    </div>
  `;
}
