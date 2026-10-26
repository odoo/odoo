import { StorePlugin } from "@mail/core/common/store_plugin";
import { getRecordLinkParams } from "@mail/utils/common/format";
import { createElementFromContent, getInnerHtml } from "@mail/utils/common/html";

import { Plugin, usePlugin } from "@odoo/owl";

import { services } from "@web/core/services";
import { renderToElement } from "@web/core/utils/render";

/** Delays in ms before fetching again the names that could not be fetched. */
const NAME_FETCH_RETRY_DELAYS = [1000, 5000, 30000];

/**
 * Links to records of this database, rendered with the name of their record. The body keeps the
 * URL: each reader sees the name of the records they can read, the others as restricted.
 */
export class RecordLinkPlugin extends Plugin {
    /** Started with the store it uses (see `StorePlugin`). */
    static sequence = 110;

    store = usePlugin(StorePlugin);
    /** @type {Map<string, Promise>} name fetch of each linked record, by "model,id" */
    nameFetches = new Map();
    /** @type {Set<string>} linked records the user can't read, by "model,id" */
    restrictedRecords = new Set();

    /**
     * Marks the links to records of this database with their model and id, for the body to render.
     *
     * @param {string|ReturnType<markup>} body
     */
    async markRecordLinks(body) {
        const bodyEl = createElementFromContent(body);
        const linkEls = [...bodyEl.querySelectorAll("a")].filter(
            (linkEl) =>
                linkEl.matches(".o_record_redirect") ||
                linkEl.textContent === linkEl.getAttribute("href")
        );
        if (!linkEls.length) {
            return body;
        }
        const records = await Promise.all(
            linkEls.map((linkEl) =>
                linkEl.textContent === linkEl.getAttribute("href") &&
                // a pasted link the composer did not render, e.g. after undo, is posted as shown
                !linkEl.matches(".o_record_redirect:not([data-oe-id])")
                    ? this.resolveRecordLink(linkEl.getAttribute("href"))
                    : undefined
            )
        );
        if (
            !records.some(Boolean) &&
            !linkEls.some((linkEl) => linkEl.matches(".o_record_redirect"))
        ) {
            return body;
        }
        linkEls.forEach((linkEl, index) => {
            const record = records[index];
            if (record) {
                linkEl.classList.add("o_record_redirect");
                linkEl.setAttribute("data-oe-model", record.model);
                linkEl.setAttribute("data-oe-id", record.id);
                return;
            }
            if (!linkEl.classList.contains("o_record_redirect")) {
                return;
            }
            linkEl.classList.remove("o_record_redirect");
            if (!linkEl.classList.length) {
                linkEl.removeAttribute("class");
            }
            linkEl.removeAttribute("data-oe-model");
            linkEl.removeAttribute("data-oe-id");
        });
        return getInnerHtml(bodyEl);
    }

    /**
     * Model and id of the record the link opens in the web client.
     *
     * @param {string} href
     */
    async resolveRecordLink(href) {
        const params = getRecordLinkParams(href);
        // the model of an action is only known by the web client
        if (params?.model && !params.action) {
            return { id: params.resId, model: params.model };
        }
    }

    /**
     * Renders the links to records that open the record they are marked with.
     *
     * @param {Iterable<HTMLAnchorElement>} linkEls
     */
    async renderRecordLinks(linkEls) {
        const recordLinks = (
            await Promise.all(
                Array.from(linkEls, async (linkEl) => {
                    const href = linkEl.getAttribute("href");
                    const model = linkEl.dataset.oeModel;
                    const id = Number(linkEl.dataset.oeId);
                    // a link with its own label is kept
                    if (!model || linkEl.textContent !== href) {
                        return;
                    }
                    // the url opens the record of the link
                    const record = await this.resolveRecordLink(href);
                    if (record?.model === model && record.id === id) {
                        return { id, linkEl, model };
                    }
                })
            )
        ).filter(Boolean);
        for (const [model, modelRecordLinks] of Object.entries(
            Object.groupBy(recordLinks, ({ model }) => model)
        )) {
            this.fetchNames(model, [...new Set(modelRecordLinks.map(({ id }) => id))]).then(() =>
                modelRecordLinks.forEach(({ id, linkEl }) =>
                    this.renderRecordLink(linkEl, { id, model })
                )
            );
        }
    }

    /**
     * Renders the link with the name of its record when known, or as restricted when the user
     * can't read it. Returns whether it is rendered.
     *
     * @param {HTMLAnchorElement} linkEl
     * @param {{ id: number, model: string }} record
     */
    renderRecordLink(linkEl, { id, model }) {
        const thread = this.store["mail.thread"].get({ model, id });
        if (!thread?.displayName && !this.restrictedRecords.has(`${model},${id}`)) {
            return false;
        }
        linkEl.classList.add("o_record_redirect_transformed");
        linkEl.replaceChildren(renderToElement("mail.Message.recordLink", { thread }));
        return true;
    }

    /**
     * Fetches the names of the linked records the user can read, once unless all attempts fail.
     *
     * @param {string} model
     * @param {number[]} ids
     */
    fetchNames(model, ids) {
        // only internal users can fetch records, the others can't read them
        if (this.store.self_user?.share !== false) {
            ids.forEach((id) => this.restrictedRecords.add(`${model},${id}`));
            return Promise.resolve();
        }
        const unfetchedIds = ids.filter(
            (id) =>
                !this.store["mail.thread"].get({ model, id })?.displayName &&
                !this.nameFetches.has(`${model},${id}`)
        );
        if (unfetchedIds.length) {
            const fetch = this.fetchNamesWithRetry(model, unfetchedIds).then(
                () =>
                    // the records the server did not return can't be read
                    unfetchedIds
                        .filter((id) => !this.store["mail.thread"].get({ model, id })?.displayName)
                        .forEach((id) => this.restrictedRecords.add(`${model},${id}`)),
                () =>
                    // fetched again on the next render
                    unfetchedIds.forEach((id) => this.nameFetches.delete(`${model},${id}`))
            );
            unfetchedIds.forEach((id) => this.nameFetches.set(`${model},${id}`, fetch));
        }
        return Promise.all(ids.map((id) => this.nameFetches.get(`${model},${id}`)));
    }

    /**
     * Retried here, as a body is only rendered again when it changes.
     *
     * @param {string} model
     * @param {number[]} ids
     * @param {number[]} [retryDelays]
     */
    async fetchNamesWithRetry(model, ids, retryDelays = NAME_FETCH_RETRY_DELAYS) {
        try {
            await this.store.fetchStoreData("record_link", { model, ids });
        } catch (error) {
            if (!retryDelays.length) {
                throw error;
            }
            await new Promise((resolve) => setTimeout(resolve, retryDelays[0]));
            return this.fetchNamesWithRetry(model, ids, retryDelays.slice(1));
        }
    }
}

services.add(RecordLinkPlugin);
