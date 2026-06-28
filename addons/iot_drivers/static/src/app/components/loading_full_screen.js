/* global owl */

import useStore from "../hooks/store_hook.js";

const { Component, xml, onMounted, props, types: t } = owl;

export class LoadingFullScreen extends Component {
    props = props({
        slots: t.object(["body"]),
    });

    store = useStore();

    setup() {
        // We delay the RPC verification to be sure that the Odoo service
        // was already restarted
        onMounted(() => {
            setTimeout(() => {
                setInterval(async () => {
                    try {
                        await this.store.rpc({
                            url: "/iot_drivers/ping",
                        });
                        window.location.reload();
                    } catch {
                        console.warn("Odoo service is probably rebooting.");
                    }
                }, 750);
            }, 2000);
        });
    }

    static template = xml`
    <div class="position-fixed top-0 start-0 bg-white vh-100 w-100 justify-content-center align-items-center d-flex flex-column gap-3 always-on-top" t-translation="off">
        <div class="spinner-border" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <t t-call-slot="body" />
    </div>
  `;
}
