/* global TYRO */

import { Component, onMounted, useState } from "@odoo/owl";
import { loadJS } from "@web/core/assets";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { TYRO_LIB_URLS } from "@pos_tyro/urls";

class GetTyroReport extends Component {
    static props = { ...standardActionServiceProps };
    static template = "pos_tyro.GetTyroReport";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.state = useState({
            loading: false,
            selectedDate: "",
            selectedType: "",
            result: "",
            message: "",
            reportLines: [],
        });

        onMounted(() =>
            this.loadTyro().catch((error) => {
                this.notification.add(error.message ?? error, { type: "danger" });
            })
        );
    }

    async loadTyro() {
        const { tyro_mode, payment_method_id, merchant_id, terminal_id } = this.props.action.params;
        if (!merchant_id || !terminal_id) {
            throw new Error("Merchant ID and/or Terminal ID are not configured.");
        }
        await loadJS(TYRO_LIB_URLS[tyro_mode]);
        const posProductInfo = await this.orm.call("pos.payment.method", "get_tyro_product_info", [
            payment_method_id,
        ]);
        this.tyroClient = new TYRO.IClient(posProductInfo.apiKey, posProductInfo);
        this.state.status = "selecting";
    }

    requestReport() {
        if (!this.state.selectedDate || !this.state.selectedType) {
            return;
        }
        this.state.loading = true;
        this.state.result = "";
        this.state.message = "Requesting Tyro Reconciliation Report";
        this.state.reportLines = [];

        const { merchant_id, terminal_id, integration_key } = this.props.action.params;
        this.tyroClient.reconciliationReport(
            {
                mid: merchant_id,
                tid: terminal_id,
                integrationKey: integration_key,
                format: "txt",
                type: this.state.selectedType,
                terminalBusinessDay: this.state.selectedDate.replaceAll("-", ""),
            },
            (response) => {
                this.state.loading = false;
                this.state.result = response.result;
                if (response.result !== "success") {
                    this.state.message = response.error;
                } else {
                    this.parseReport(response.data);
                }
            }
        );
    }

    parseReport(reportData) {
        const lines = reportData
            .split("\n")
            .filter((line) => line.length > 0)
            .map((line) => {
                return line.replace(/NEW_LINE|FORM_FEED/, "");
            })
            .map((line) => {
                const classList = [];
                if (line.includes("_CENTRED")) {
                    classList.push("align-self-center");
                } else if (line.includes("_RIGHT")) {
                    classList.push("align-self-end");
                }
                if (line.includes("_BOLD")) {
                    classList.push("fw-bolder");
                }
                if (line.startsWith("LARGE")) {
                    classList.push("fs-3", "fw-bolder");
                }
                const trimmedLine = line.replace(/^[A-Z_]*: /, "");
                return [trimmedLine, classList.join(" ")];
            });
        this.state.reportLines = lines;
    }
}

registry.category("actions").add("get_tyro_report", GetTyroReport);
