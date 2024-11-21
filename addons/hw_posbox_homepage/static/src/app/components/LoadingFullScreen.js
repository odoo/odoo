/* global owl */

import useStore from "../hooks/useStore.js";

const { Component, xml, onMounted } = owl;

export class LoadingFullScreen extends Component {
    static props = {
        slots: Object,
    };

    setup() {
        this.store = useStore();

        // We delay the RPC verification for 10 seconds to be sure that the Odoo service
        // was already restarted
        onMounted(() => {
            setTimeout(() => {
                setInterval(async () => {
                    try {
                        await this.store.rpc({
                            url: "/hw_posbox_homepage/ping",
                        });
                        window.location.reload();
                    } catch {
                        console.warn("Odoo service is probably rebooting.");
                    }
                }, 750);
            }, 10000);
        });
    }

    static template = xml`
    <div class="position-fixed top-0 start-0 bg-white vh-100 w-100 justify-content-center align-items-center d-flex flex-column gap-3" style="z-index: 9999">
        <div class="spinner-border" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
        <t t-slot="body" />
    </div>
  `;
}
