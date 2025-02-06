import { _t } from "@web/core/l10n/translation";
import { parseFloat } from "@web/views/fields/parsers";
import { Transition } from "@web/core/transition";
import { useBus, useService } from "@web/core/utils/hooks";

import { useRef, useState, Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { serializeDateTime } from "@web/core/l10n/dates";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { pick } from "@web/core/utils/objects";
const { DateTime } = luxon;

const useDialogDraggable = makeDraggableHook({
    name: "useDialogDraggable",
    onWillStartDrag({ ctx, addCleanup, addStyle, getRect }) {
        ctx.current.container = document.createElement("div");
        const { height } = getRect(ctx.current.element);
        addStyle(ctx.current.container, {
            position: "fixed",
            top: "0",
            bottom: `${height}px`,
            left: "0",
            right: "0",
        });
        ctx.current.element.after(ctx.current.container);
        addCleanup(() => ctx.current.container.remove());
    },
    onDrop: ({ ctx, getRect }) => pick(getRect(ctx.current.element), "left", "top"),
});

export class DebugWidget extends Component {
    static components = { Transition };
    static template = "point_of_sale.DebugWidget";
    static props = { state: { type: Object, shape: { showWidget: Boolean } } };
    setup() {
        this.pos = usePos();
        this.debug = useService("debug");
        this.barcodeReader = useService("barcode_reader");
        this.hardwareProxy = useService("hardware_proxy");
        this.notification = useService("notification");
        const numberBuffer = useService("number_buffer");
        this.dialog = useService("dialog");
        useBus(numberBuffer, "buffer-update", this._onBufferUpdate);
        this.state = useState({
            barcodeInput: "",
            weightInput: "",
            buffer: numberBuffer.get(),
        });
        this.root = useRef("root");
        this.position = useState({ left: null, top: null });
        useDialogDraggable({
            ref: this.root,
            elements: ".debug-widget",
            handle: ".drag-handle",
            onDrop: ({ left, top }) => {
                this.position.left = left;
                this.position.top = top;
            },
        });

        // Make the background of the "hardware events" section flash when a corresponding message
        // is sent to the proxy.
        for (const eventName of ["open_cashbox", "print_receipt", "scale_read"]) {
            const ref = useRef(eventName);
            let animation;
            useBus(this.hardwareProxy, `send_message:${eventName}`, () => {
                animation?.cancel();
                animation = ref.el?.animate({ backgroundColor: ["#6CD11D", "#1E1E1E"] }, 2000);
            });
        }
    }
    toggleWidget() {
        this.state.isShown = !this.state.isShown;
    }
    setWeight() {
        var weightInKg = parseFloat(this.state.weightInput);
        if (!isNaN(weightInKg)) {
            this.hardwareProxy.setDebugWeight(weightInKg);
        }
    }
    resetWeight() {
        this.state.weightInput = "";
        this.hardwareProxy.resetDebugWeight();
    }
    async barcodeScan() {
        if (!this.barcodeReader) {
            return;
        }
        await this.barcodeReader.scan(this.state.barcodeInput);
    }
    async barcodeScanEAN() {
        if (!this.barcodeReader) {
            return;
        }
        const ean = this.barcodeReader.parser.sanitize_ean(this.state.barcodeInput || "0");
        this.state.barcodeInput = ean;
        await this.barcodeReader.scan(ean);
    }
    _createBlob(contents) {
        if (typeof contents !== "string") {
            contents = JSON.stringify(contents, null, 2);
        }
        return new Blob([contents]);
    }
    deleteOrders({ paid = true } = {}) {
        this.dialog.add(ConfirmationDialog, {
            title: _t("Delete Orders?"),
            body: _t(
                `This operation will destroy all ${
                    paid ? "paid" : "unpaid"
                } orders in the browser. You will lose all the data. This operation cannot be undone.`
            ),
            confirm: () => {
                this.pos.data.resetUnsyncQueue();
                const orders = this.pos.models["pos.order"].filter(
                    (order) => order.finalized === paid
                );

                for (const order of orders) {
                    this.pos.data.localDeleteCascade(order, !paid);
                }

                if (!this.pos.get_order()) {
                    this.pos.add_new_order();
                }
            },
        });
    }
    exportOrders({ paid = true } = {}) {
        const orders = this.pos.models["pos.order"]
            .filter((order) => order.finalized === paid)
            .map((o) => o.serialize({ orm: true }));

        const blob = this._createBlob(orders);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        const fileName = `${paid ? "paid" : "unpaid"}_orders_${serializeDateTime(
            DateTime.now()
        ).replace(/:|\s/gi, "-")}.json`;

        a.href = url;
        a.download = fileName;
        a.click();
    }
    async importOrders(event) {
        const file = event.target.files[0];
        if (file) {
            const jsonData = JSON.parse(await file.text());
            const data = {
                "pos.order": [],
            };
            const manyRel = Object.values(this.pos.data.relations["pos.order"]).filter((rel) =>
                ["one2many", "many2many"].includes(rel.type)
            );

            for (const order of jsonData) {
                for (const rel of manyRel) {
                    const model = this.pos.models[rel.relation];

                    if (!model) {
                        continue;
                    }

                    if (!order[rel.name] && (rel.local || rel.related || rel.compute)) {
                        order[rel.name] = [];
                    }

                    const existingRecords = model.getAllBy("id");
                    const records = order[rel.name]
                        .filter((rel) => !existingRecords[rel[2]])
                        .map((rel) => rel[2]);

                    if (!data[rel.relation]) {
                        data[rel.relation] = [];
                    }

                    data[rel.relation].push(...records);
                }

                data["pos.order"].push(order);
            }

            const missing = await this.pos.data.missingRecursive(data);
            this.pos.data.models.loadData(missing, [], true);
            this.notification.add(_t("%s orders imported", data["pos.order"].length));
        }
    }
    refreshDisplay() {
        this.hardwareProxy.message("display_refresh", {});
    }
    _onBufferUpdate({ detail: value }) {
        this.state.buffer = value;
    }
    get bufferRepr() {
        return `"${this.state.buffer}"`;
    }
    get style() {
        const { left, top } = this.position;
        return top === null ? "" : `position: absolute; left: ${left}px; top: ${top}px;`;
    }
}
