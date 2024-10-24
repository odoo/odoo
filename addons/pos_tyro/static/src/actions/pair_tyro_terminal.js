/* global TYRO */

import { Component, useState, onMounted } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { TYRO_LIB_URLS } from "@pos_tyro/urls";

const PAIRING_TIMEOUT_MS = 90000;

class PairTyroTerminal extends Component {
    static template = "pos_tyro.PairTyroTerminal";

    setup() {
        this.orm = useService("orm");
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.state = useState({
            status: "inProgress",
            message: "Connecting to Tyro...",
            closed: false,
        });

        onMounted(() =>
            this.createTyroTerminal().catch((error) => {
                this.notification.add(error.message ?? error, { type: "danger" });
                this.dialog.closeAll();
                this.ui.unblock();
            })
        );
    }

    async createTyroTerminal() {
        const { tyro_mode, payment_method_id, merchant_id, terminal_id } = this.props.action.params;
        if (!merchant_id || !terminal_id) {
            throw new Error("Merchant ID and/or Terminal ID are not configured.");
        }
        await loadJS(TYRO_LIB_URLS[tyro_mode]);
        const posProductInfo = await this.orm.call("pos.payment.method", "get_tyro_product_info", [
            payment_method_id,
        ]);
        const tyroClient = new TYRO.IClient(posProductInfo.apiKey, posProductInfo);

        setTimeout(() => {
            this.ui.unblock();
            this.state.message = "Pairing timed out.";
            this.state.status = "failure";
        }, PAIRING_TIMEOUT_MS);
        this.ui.block({ delay: PAIRING_TIMEOUT_MS });

        tyroClient.pairTerminal(merchant_id, terminal_id, (response) => {
            if (this.state.closed) {
                return;
            }
            this.state.status = response.status;
            this.state.message = response.message;
            if (response.status !== "inProgress") {
                this.ui.unblock();
            }
            if (response.status === "success") {
                this.orm.write("pos.payment.method", [payment_method_id], {
                    tyro_integration_key: response.integrationKey,
                });
            }
        });
    }
}

registry.category("actions").add("pair_tyro_terminal", PairTyroTerminal);
