import { computed, signal, Component, onWillStart } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { registry } from "@web/core/registry";
import { Mutex } from "@web/core/utils/concurrency";
import { useBus, useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

import { ProductLine } from "./product_line/product_line";

export class AllocationReport extends Component {
    static template = "stock.AllocationReport";
    static components = {
        CheckBox,
        ProductLine,
    }
    static props = { ...standardActionServiceProps }

    canPrintLabels = computed(() => {
        for (const productLine of this.productLines || []) {
            if (productLine.needs.some((need) => need.isReserved(), productLine.needs)) {
                return true;
            }
        }
        return false;
    })

    canAssignAll = computed(() => {
        if (!this.hasContent) {
            return false;
        }
        return this.productLines.some((line) =>
            line.freeQty() > 0 && line.needs && line.needs.some((need) => need.allocateQuantity())
        );
    })

    setup() {
        this.actionService = useService("action");
        this.ormService = useService("orm");
        this.ui = useService("ui");
        this.context = this.props.action.context;
        this.mutex = new Mutex();
        this._onGoingJob = false;

        useBus(this.env.bus, "print_labels", (ev) => this.onPrintLabels(ev.detail));
        useBus(this.env.bus, "open_record", (ev) => this.openRecord(ev.detail));

        onWillStart(async () => {
            this.data = await this.getReportData();
            this.doc = this.data.doc;
            this.setupProductLines();
            this.hasContent = this.data.product_lines.length;
        });
    }

    setupProductLines() {
        this.productLines = [];
        this.productLinesById = {};
        for (const data of this.data.product_lines) {
            const needsByOperations = this._defineProductLineNeeds(data.needs);
            const productLine = {
                freeQty: signal(data.free_qty),
                id: data.id,
                name: data.display_name,
                uom: data.uom,
                needsByOperations,
                needs: Object.values(needsByOperations),
                sourceIds: data.move_ids,
                totalQty: data.total_qty,
                updateMoveReservation: this.updateMoveReservation.bind(this),
            };
            this.shareQuantity(productLine);
            this.productLines.push(productLine);
            this.productLinesById[data.id] = productLine;
        }
    }

    _defineProductLineNeeds(needs) {
        const needsByOperations = {};
        for (const outMove of needs) {
            const key = this._getOperationKey(outMove);
            if (!needsByOperations[key]) {
                needsByOperations[key] = {
                    allocateQuantity: signal(0),
                    availableQuantity: 0,
                    isReserved: signal(false),
                    moves: [outMove],
                };
            } else {
                const moveIndex = needsByOperations[key].moves.findIndex(
                    move => move.id === outMove.id
                );
                if (moveIndex === -1) {
                    needsByOperations[key].moves.push(outMove);
                } else {
                    needsByOperations[key].moves[moveIndex] = outMove;
                }
            }
        }
        return needsByOperations;
    }

    synchroniseUpdatedMoves(productLine, updatedOutMoves) {
        updatedOutMoves = [...updatedOutMoves]; // Shallow copy to avoid modifying origin argument.
        const key = this._getOperationKey(updatedOutMoves[0]);
        const needMoves = productLine.needsByOperations[key].moves;
        // Iterate on known moves in order to update them.
        for (let i = (needMoves.length - 1); i >= 0; i--) {
            const needMove = needMoves[i];
            let updated = false;
            for (let j = (updatedOutMoves.length - 1); j >= 0; j--) {
                const move = updatedOutMoves[j];
                if (needMove.id === move.id) {
                    // Update hte component's move values and remove if from `updatedOutMoves`.
                    Object.assign(needMove, move);
                    updatedOutMoves.splice(j, 1);
                    updated = true;
                }
            }
            if (!updated) {
                // The move wasn't found, which means it was probably merged so we remove it.
                needMoves.splice(i, 1);
            }
        }
        // All remaining `updatedOutMoves` are added (new moves, probably
        // created by split an existing move).
        if (updatedOutMoves.length) {
            needMoves.push(...updatedOutMoves);
        }
    }

    async updateMoveReservation(toReserve, productId, outLine) {
        if (this._onGoingJob) {
            return; // Prevent concurrency errors.
        }
        const productLine = this.productLinesById[productId];
        this._onGoingJob = this.mutex.exec(
            async () => await this._updateMoveReservation(toReserve, productLine, outLine)
        );
        this._onGoingJob.then(() => {
            this._onGoingJob = false;
        });
    }

    async _updateMoveReservation(toReserve, productLine, outLine) {
        // const outIds = outLine.moves().map(move => move.id);
        const outIds = outLine.moves.map(move => move.id);
        if (toReserve) {
            // Do the allocation.
            const notAssignedMoves = outLine.moves
                .filter(move => !move.is_reserved && !move.move_orig_ids.length);
            const outDemandQty = notAssignedMoves.reduce((qty, move) => qty += move.quantity, 0);
            const quantityToReserve = Math.min(productLine.freeQty(), outDemandQty);
            if (!quantityToReserve) {
                return; // Avoid useless RPC if nothing to reserve.
            }
            const updatedData = await this.ormService.call(
                "stock.allocation.report",
                "action_assign",
                [productLine.sourceIds, outIds, quantityToReserve],
            );
            productLine.sourceIds = updatedData.in_moves;
            this.synchroniseUpdatedMoves(productLine, updatedData.out_moves);
            productLine.freeQty.set(productLine.freeQty() - quantityToReserve);
        } else {
            // Free allocated quantity.
            const quantityToFree = outLine.allocateQuantity() || outLine.moves.reduce(
                (qtySum, move) => qtySum + (move.is_reserved ? move.quantity : 0), 0
            );
            const updatedData = await this.ormService.call(
                "stock.allocation.report",
                "action_unassign",
                [productLine.sourceIds, outIds, quantityToFree],
            );
            productLine.sourceIds = updatedData.in_moves;
            this.synchroniseUpdatedMoves(productLine, updatedData.out_moves);
            // Take account of freed quantity.
            productLine.freeQty.set(productLine.freeQty() + updatedData.freed_quantity);
        }
        return this.shareQuantity(productLine);
    }

    /**
     * Share available quantity between all needs.
     */
    shareQuantity(productLine) {
        let quantityToAllocate = productLine.freeQty();
        for (const outLine of productLine.needs) {
            outLine.allocateQuantity = outLine.allocateQuantity || signal(0);
            outLine.isReserved = outLine.isReserved || signal(false);
            outLine.reservedQuantity = outLine.reservedQuantity || signal(0);

            let allocateQuantity = 0;
            let reservedQuantity = 0;
            let isReserved = false;
            for (const outMove of outLine.moves) {
                const hasOriginMoves = Boolean(outMove.move_orig_ids.length);
                isReserved = isReserved || outMove.is_reserved || hasOriginMoves;
                if (!outMove.is_reserved && quantityToAllocate > 0) {
                    const qtyForThisNeed = Math.min(quantityToAllocate, outMove.quantity);
                    allocateQuantity += qtyForThisNeed;
                    quantityToAllocate -= qtyForThisNeed;
                } else if (outMove.is_reserved) {
                    reservedQuantity += outMove.quantity;
                }
            }
            outLine.allocateQuantity.set(allocateQuantity);
            if (outLine.hidden === undefined) {
                // Set `hidden` only once to not override it when `shareQuantity` is called again.
                outLine.hidden = signal(!(allocateQuantity || reservedQuantity));
            }
            outLine.isReserved.set(isReserved);
            outLine.reservedQuantity.set(reservedQuantity);
        }
    }

    _getOperationKey(outMove) {
        let key = outMove.picking ? `stock.picking_${outMove.picking.id}` : "0";
        if (outMove.source) {
            key += `,${outMove.source.res_model}_${outMove.source.id}`;
        }
        return key;
    }

    async getReportData() {
        const context = { ...this.context };
        const args = [
            { context, report_type: "html" },
        ];
        if (!context.active_ids) {
            if (context.active_id) {
                context.active_ids = [context.active_id];
            } else if (context.default_picking_ids) {
                context.active_ids = context.default_picking_ids;
                context.active_model = "stock.picking";
            }
        }
        if (!context.active_model || !context.active_ids) {
            // Try to find active model and id from the URL if they are missing from the context.
            const { breadcrumbs } = this.env.config;
            const url = breadcrumbs.length > 1 ? breadcrumbs[breadcrumbs.length - 2].url : "";
            const idAndModel = this._findIndexAndModelFromURL(url);
            if (idAndModel) {
                context.active_ids = [idAndModel[0]];
                context.active_model = idAndModel[1];
            }
        }
        return this.ormService.call(
            "stock.allocation.report",
            "get_report_data",
            args,
            { context },
        );
    }

    _findIndexAndModelFromURL(url) {
        const data = url.split("/").reverse();
        const idIndex = data.findIndex((d) => d && !isNaN(d));
        const modelIndex = idIndex + 1;
        if (modelIndex < data.length) {
            const resModel = this._getResModelFromPath(data[modelIndex]);
            if (resModel) {
                return [Number(data[idIndex]), resModel];
            }
        }
        return false;
    }

    _getResModelFromPath(str) {
        if (["receipts", "internal"].includes(str)) {
            return "stock.picking";
        }
        return false;
    }

    openRecord(record) {
        return this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: record.res_model,
            res_id: record.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    goBack(record) {
        if (record && this.env.config.breadcrumbs.length === 1) {
            this.openRecord(record);
        } else {
            this.env.config.historyBack();
        }
    }

    async printLabels(docids, movesQty) {
        const data = { docids, quantity: movesQty.join(",") };
        const context = { active_ids: docids };
        if (!this.reportAction) {
            // Fetch report data only once and only if needed.
            this.reportAction = (await this.ormService.searchRead("ir.actions.report", [
                ["report_name", "=", "stock.report_reception_report_label"],
            ]))[0];
        }
        return this.actionService.doAction({ ...this.reportAction, context, data });
    }

    onClickAssignAll() {
        if (this._onGoingJob) {
            return; // Prevent concurrency errors.
        }
        const allocationsData = [];
        for (const productLine of this.productLines) {
            const allocionData = [productLine.sourceIds, []];
            for (const need of productLine.needs) {
                const possibleAllocationQty = need.allocateQuantity();
                if (possibleAllocationQty) {
                    const moveIds = need.moves.map((move) => move.id);
                    allocionData[1].push([moveIds, possibleAllocationQty]);
                }
            }
            allocationsData.push(allocionData);
        }
        this._onGoingJob = this.mutex.exec(async () => {
            const updatedData = await this.ormService.call(
                "stock.allocation.report",
                "action_assign_all",
                [allocationsData],
            );
            for (const [productId, data] of Object.entries(updatedData)) {
                const productLine = this.productLines.find((line) => line.id === Number(productId));
                productLine.sourceIds = data.in_moves;
                let allocatedQuantity = 0;
                for (const updatedOutMoves of data.out_moves) {
                    this.synchroniseUpdatedMoves(productLine, updatedOutMoves);
                    const outMovesAllocatedQty = updatedOutMoves.reduce(
                        (sum, move) => move.is_reserved ? sum + move.quantity : sum, 0
                    );
                    allocatedQuantity += outMovesAllocatedQty;
                }
                productLine.freeQty.set(productLine.freeQty() - allocatedQuantity);
                this.shareQuantity(productLine);
            }
        });
        this._onGoingJob.then(() => {
            this._onGoingJob = false;
        });
    }

    async onClickPrint() {
        const { res_model, id } = this.doc;
        const printAction = await this.ormService.call(res_model, "do_print_picking", [id]);
        return this.actionService.doAction(printAction);
    }

    async onClickPrintLabels() {
        const docids = [];
        const movesQty = [];
        for (const productLine of this.data.product_lines) {
            for (const need of productLine.needs) {
                if (need.state === "is_waiting" || need.is_reserved) {
                    docids.push(need.id);
                    movesQty.push(need.reserved_quantity || need.quantity);
                }
            }
        }
        if (docids.length) {
            return this.printLabels(docids, movesQty);
        }
    }

    onPrintLabels({ docids, movesQty }) {
        return this.printLabels(docids, movesQty);
    }
}

registry.category("actions").add("allocation_report", AllocationReport);
