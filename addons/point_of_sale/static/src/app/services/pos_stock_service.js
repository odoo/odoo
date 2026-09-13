// @ts-check
/** @odoo-module native */
import { reactive } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";

import { logPosMessage } from "../utils/pretty_console_log.js";
const log = makeLogger("pos.stock");

export class PosStockService {
    /**
     * @param {object} env
     * @param {{ orm: any, pos: any }} deps
     */
    constructor(env, { orm, pos }) {
        this.orm = orm;
        this.pos = pos;
        /** @type {Record<number, number | null>} */
        this.quantities = reactive({});
        /** @type {Set<number>} */
        this.pending = new Set();
        /** @type {Set<number>} */
        this.inFlight = new Set();
        this.generation = 0;
        this.flushScheduled = false;
    }

    /**
     * @param {Iterable<number>} productIds
     */
    request(productIds) {
        let added = 0;
        for (const id of productIds) {
            if (
                !(id in this.quantities) &&
                !this.pending.has(id) &&
                !this.inFlight.has(id)
            ) {
                this.pending.add(id);
                added++;
            }
        }
        log.logic("request", () => ({
            added,
            pending: this.pending.size,
            schedule: this.pending.size > 0 && !this.flushScheduled,
        }));
        if (this.pending.size && !this.flushScheduled) {
            this.flushScheduled = true;
            Promise.resolve().then(() => this.flush());
        }
    }

    refresh() {
        const known = new Set([
            ...Object.keys(this.quantities).map(Number),
            ...this.pending,
            ...this.inFlight,
        ]);
        this.generation++;
        this.inFlight.clear();
        log.pipeline("refresh", () => ({
            known: known.size,
            generation: this.generation,
        }));
        for (const id of known) {
            delete this.quantities[id];
        }
        this.request(known);
    }

    async flush() {
        this.flushScheduled = false;
        const ids = [...this.pending];
        this.pending.clear();
        if (!ids.length) {
            return;
        }
        const generation = this.generation;
        for (const id of ids) {
            this.inFlight.add(id);
        }
        const endFlush = log.perf("flush get_pos_stock_quantities");
        try {
            const result = await this.orm.call(
                "product.product",
                "get_pos_stock_quantities",
                [ids, this.pos.config.id],
            );
            if (generation !== this.generation) {
                log.logic("flush: stale response ignored", () => ({ generation }));
                return;
            }
            for (const id of ids) {
                this.quantities[id] = result[id] ?? 0;
            }
        } catch (error) {
            if (generation !== this.generation) {
                log.logic("flush: stale failure ignored", () => ({ generation }));
                return;
            }
            for (const id of ids) {
                this.quantities[id] = null;
            }
            logPosMessage(
                "PosStockService",
                "flush",
                "Quantity fetch failed",
                undefined,
                [error],
            );
        } finally {
            if (generation === this.generation) {
                for (const id of ids) {
                    this.inFlight.delete(id);
                }
            }
            endFlush({ products: ids.length, stale: generation !== this.generation });
        }
    }
}

export const posStockService = {
    dependencies: ["orm", "pos"],
    /**
     * @param {object} env
     * @param {{ orm: any, pos: any }} deps
     */
    start(env, { orm, pos }) {
        return new PosStockService(env, { orm, pos });
    },
};

registry.category("services").add("pos_stock", posStockService);
