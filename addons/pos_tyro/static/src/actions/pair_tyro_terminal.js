import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { TYRO_LIB_URLS } from "@pos_tyro/urls";

const PAIRING_TIMEOUT_MS = 90000;

class PairTyroTerminal extends Component {
    static props = { ...standardActionServiceProps };
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
            this.pairTyroTerminal().catch((error) => {
                this.notification.add(error.message ?? error, { type: "danger" });
                this.dialog.closeAll();
                this.ui.unblock();
            })
        );

        onWillUnmount(() => {
            if (this.state.timeoutId) {
                clearTimeout(this.state.timeoutId);
            }
        });
    }

    async loadTyroLibrary(tyroMode) {
        if (!window.tyroLib) {
            window.tyroLib = {};
        }

        if (!window.tyroLib[tyroMode]) {
            await loadJS(TYRO_LIB_URLS[tyroMode]);
            window.tyroLib[tyroMode] = window.TYRO;
        }

        return window.tyroLib[tyroMode];
    }

    async pairTyroTerminal() {
        const { tyro_mode, payment_method_id, merchant_id, terminal_id } = this.props.action.params;
        if (!merchant_id || !terminal_id) {
            throw new Error("Merchant ID and/or Terminal ID are not configured.");
        }

        const tyro = await this.loadTyroLibrary(tyro_mode);
        const posProductInfo = await this.orm.call("pos.payment.method", "get_tyro_product_info", [
            payment_method_id,
        ]);
        const tyroClient = new tyro.IClient(posProductInfo.apiKey, posProductInfo);

        this.state.timeoutId = setTimeout(() => {
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
