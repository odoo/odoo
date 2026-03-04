import { Component, useState, useEffect } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";
import { Input } from "@point_of_sale/app/components/inputs/input/input";

export class MpesaTransactionPopup extends Component {
    static components = { Dialog, Input };
    static template = "pos_safaricom.MpesaTransactionPopup";
    static props = {
        close: Function,
        getPayload: Function,
        qrCode: { type: String, optional: true },
    };

    setup() {
        this.pos = usePos();
        this.state = useState({
            transactions: [],
            showQrCode: false,
            searchQuery: "",
        });
        this.ui = useService("ui");
        this.tx = null;
        useEffect(
            () => {
                this.updateTransactions();
            },
            () => [this.pos.lipaLastNotificationTime]
        );
    }

    async updateTransactions() {
        const records = await this.pos.data.searchRead("transaction.lipa.na.mpesa", []);
        if (records.length > 0) {
            this.state.transactions = records
                .map((r) => ({
                    id: r.id,
                    name: r.name,
                    phone: r.number,
                    amount: r.amount,
                    received_at: r.received_at,
                }))
                .reverse();
        }
    }

    confirm(tx) {
        this.props.getPayload(tx);
        this.props.close();
    }

    cancel() {
        this.props.close();
    }

    toggleQrCode() {
        this.state.showQrCode = !this.state.showQrCode;
    }

    get transactions() {
        if (!this.state.searchQuery) {
            return this.state.transactions;
        }

        const search = this.state.searchQuery;
        return this.state.transactions.filter(
            (transaction) =>
                transaction.name.toLowerCase().includes(search.toLowerCase()) ||
                transaction.phone.toLowerCase().includes(search.toLowerCase())
        );
    }
}
