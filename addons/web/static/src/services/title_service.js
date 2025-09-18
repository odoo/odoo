// @ts-check

/** @module @web/services/title_service - Manages the document title with named parts and notification counters */

/**
 * @typedef {Object} TitleServiceAPI
 * @property {string} current - the current document.title value (readonly)
 * @property {() => Record<string, string>} getParts - get a copy of the title parts
 * @property {(counters: Record<string, number>) => void} setCounters - set notification counters
 * @property {(parts: Record<string, string | null>) => void} setParts - set title segments
 */

/** Service that manages the document title with named parts and notification counters. */
import { registry } from "@web/core/registry";
export const titleService = {
    /** @returns {TitleServiceAPI} */
    start() {
        /** @type {Record<string, number>} */
        const titleCounters = {};
        /** @type {Record<string, string>} */
        const titleParts = {};

        /**
         * Return a shallow copy of the current title parts.
         * @returns {Record<string, string>}
         */
        function getParts() {
            return { ...titleParts };
        }

        /**
         * @param {Record<string, number>} counters
         */
        function setCounters(counters) {
            for (const key in counters) {
                const val = counters[key];
                if (!val) {
                    delete titleCounters[key];
                } else {
                    titleCounters[key] = val;
                }
            }
            updateTitle();
        }

        /**
         * @param {Record<string, string | null>} parts
         */
        function setParts(parts) {
            for (const key in parts) {
                const val = parts[key];
                if (!val) {
                    delete titleParts[key];
                } else {
                    titleParts[key] = val;
                }
            }
            updateTitle();
        }

        /** Recompute document.title from parts and counters. */
        function updateTitle() {
            const counter = Object.values(titleCounters).reduce(
                (acc, count) => acc + count,
                0,
            );
            const name = Object.values(titleParts).join(" - ") || "Odoo";
            if (!counter) {
                document.title = name;
            } else {
                document.title = `(${counter}) ${name}`;
            }
        }

        return {
            /**
             * @returns {string}
             */
            get current() {
                return document.title;
            },
            getParts,
            setCounters,
            setParts,
        };
    },
};

registry.category("services").add("title", titleService);
