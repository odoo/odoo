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
            searchPhoneHash: "",
        });
        this.ui = useService("ui");
        this.tx = null;
        useEffect(
            () => {
                this.updateTransactions();
            },
            () => [this.pos.lipaLastNotificationTime]
        );
        useEffect(
            (search) => {
                this.hashPhone(search).then((hash) => {
                    if (search === this.state.searchQuery) {
                        this.state.searchPhoneHash = hash;
                    }
                });
            },
            () => [this.state.searchQuery]
        );
    }

    async hashPhone(search) {
        // C2B confirmations carry the SHA-256 of the 254XXXXXXXXX number as MSISDN
        const digits = search.replace(/\D/g, "").replace(/^0+/, "");
        if (!digits) {
            return "";
        }
        const phone = digits.startsWith("254") ? digits : "254" + digits;
        const digest = await window.crypto.subtle.digest(
            "SHA-256",
            new TextEncoder().encode(phone)
        );
        return Array.from(new Uint8Array(digest), (byte) =>
            byte.toString(16).padStart(2, "0")
        ).join("");
    }

    async updateTransactions() {
        const records = await this.pos.data.searchRead("transaction.lipa.na.mpesa", []);
        const paidTransIds = new Set(this.pos.models["pos.payment"].map((p) => p.transaction_id));
        if (records.length > 0) {
            this.state.transactions = records
                .filter((r) => !paidTransIds.has(r.trans_id))
                .map((r) => ({
                    id: r.id,
                    name: r.name,
                    phone: r.number,
                    amount: r.amount,
                    received_at: r.received_at,
                    trans_id: r.trans_id,
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
                transaction.phone === this.state.searchPhoneHash ||
                transaction.trans_id.toLowerCase().includes(search.toLowerCase())
        );
    }
}
