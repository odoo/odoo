import { Plugin } from "@html_editor/plugin";
import { generatePartnerMentionElement } from "@mail/utils/common/format";

const MENTION_SELECTOR = "a.o_mail_redirect, a.o-discuss-mention";
/** Fields needed to know whether a record can be mentioned. */
const MENTIONED_RECORD_FIELDS = {
    "res.partner": ["name", "partner_share"],
    "res.role": ["name", "user_ids_count"],
};

/**
 * Turns an inserted mention (e.g. pasted) into text when it would not notify, and gives the
 * mentioned records to `composerPluginDependencies.onMentions`. Loaded mentions are kept as is.
 */
export class MentionPlugin extends Plugin {
    static id = "mention";
    static dependencies = ["history"];
    static shared = ["syncPartnerMentions", "whenMentionsChecked"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        before_insert_processors: (container) => {
            for (const mentionEl of container.querySelectorAll(MENTION_SELECTOR)) {
                this.insertMention(mentionEl);
            }
            return container;
        },
        normalize_processors: (root) => {
            const mentionEls = [...root.querySelectorAll(MENTION_SELECTOR)];
            if (root.matches(MENTION_SELECTOR)) {
                mentionEls.push(root);
            }
            for (const mentionEl of mentionEls) {
                if (mentionEl.getAttribute("contenteditable") !== "false") {
                    mentionEl.setAttribute("contenteditable", "false");
                }
            }
            return root;
        },
        on_content_updated_handlers: () => (this.mentionsChecked = this.updateMentions()),
        on_editor_started_handlers: () => (this.mentionsChecked = this.updateMentions()),
        selectors_for_feff_providers: () => MENTION_SELECTOR,
    };

    /** @type {Map<string, Promise<import("models").ResPartner|import("models").ResRole|undefined>>} */
    mentionFetches = new Map();
    /** @type {WeakSet<HTMLAnchorElement>} */
    insertedMentions = new WeakSet();
    /** @type {Promise<void>} */
    mentionsChecked = Promise.resolve();
    /**
     * Mentions turned into text, kept as mentions when undo brings them back.
     *
     * @type {WeakSet<HTMLAnchorElement>}
     */
    unlinkedMentions = new WeakSet();

    /**
     * Turns the mention into text in its insertion step when it is known not to notify.
     *
     * @param {HTMLAnchorElement} mentionEl
     */
    insertMention(mentionEl) {
        const { oeId, oeModel } = mentionEl.dataset;
        const isRecordMention = Object.hasOwn(MENTIONED_RECORD_FIELDS, oeModel ?? "");
        const record = isRecordMention
            ? this.services["mail.store"][oeModel].get(Number(oeId))
            : undefined;
        const isKnown = !isRecordMention || record?.name !== undefined;
        if (isKnown && !this.isNotifyingMention(mentionEl, record)) {
            mentionEl.replaceWith(this.document.createTextNode(mentionEl.textContent));
            return;
        }
        this.insertedMentions.add(mentionEl);
    }

    /** Resolved once the mentions are given to the composer, which waits for it to post. */
    whenMentionsChecked() {
        return this.mentionsChecked;
    }

    /** Same as `insertMention` once the records are fetched, and gives them to the composer. */
    async updateMentions() {
        const mentionEls = [...this.editable.querySelectorAll(MENTION_SELECTOR)];
        const results = await Promise.allSettled(
            mentionEls.map((mentionEl) => this.fetchMentionedRecord(mentionEl))
        );
        if (this.isDestroyed) {
            return;
        }
        const partners = [];
        const roles = [];
        const invalidMentionEls = [];
        for (const [index, mentionEl] of mentionEls.entries()) {
            // not checked when its record could not be fetched
            if (results[index].status === "rejected" || !this.editable.contains(mentionEl)) {
                continue;
            }
            const record = results[index].value;
            if (!this.isNotifyingMention(mentionEl, record)) {
                if (this.insertedMentions.has(mentionEl) && !this.unlinkedMentions.has(mentionEl)) {
                    invalidMentionEls.push(mentionEl);
                }
            } else if (mentionEl.dataset.oeModel === "res.partner") {
                partners.push(record);
            } else if (mentionEl.dataset.oeModel === "res.role") {
                roles.push(record);
            }
        }
        if (invalidMentionEls.length) {
            invalidMentionEls.forEach((mentionEl) => this.unlinkMention(mentionEl));
            this.dependencies.history.commit();
        }
        this.config.composerPluginDependencies.onMentions({ partners, roles });
    }

    /**
     * Whether the mention notifies once posted, as checked on post.
     *
     * @param {HTMLAnchorElement} mentionEl
     * @param {import("models").ResPartner|import("models").ResRole} [record]
     */
    isNotifyingMention(mentionEl, record) {
        const store = this.services["mail.store"];
        const thread = this.config.composerPluginDependencies.getThread();
        const text = mentionEl.textContent;
        const { oeModel } = mentionEl.dataset;
        if (mentionEl.classList.contains("o_mail_redirect")) {
            return (
                oeModel === "res.partner" &&
                Boolean(record) &&
                // only internal users can mention a partner without its token
                (store.self_user?.share === false || Boolean(record.mention_token)) &&
                store.getPartnerMentionTexts(record, thread).some((t) => text.includes(t))
            );
        }
        if (oeModel) {
            return oeModel === "res.role" && Boolean(record) && text.includes(`@${record.name}`);
        }
        return store.specialMentions.some(
            (special) =>
                special.channel_types.includes(thread?.channel?.channel_type) &&
                text.includes(`@${special.label}`)
        );
    }

    /**
     * Special mentions (e.g. @everyone) have no record.
     *
     * @param {HTMLAnchorElement} mentionEl
     */
    fetchMentionedRecord(mentionEl) {
        const { oeId, oeModel } = mentionEl.dataset;
        if (!Object.hasOwn(MENTIONED_RECORD_FIELDS, oeModel ?? "")) {
            return Promise.resolve();
        }
        const store = this.services["mail.store"];
        // only internal users can fetch roles
        if (oeModel === "res.role" && store.self_user?.share !== false) {
            return Promise.resolve(store["res.role"].get(Number(oeId)));
        }
        const key = `${oeModel},${oeId}`;
        if (!this.mentionFetches.has(key)) {
            this.mentionFetches.set(
                key,
                store[oeModel]
                    .getOrFetch(Number(oeId), MENTIONED_RECORD_FIELDS[oeModel])
                    .catch((error) => {
                        // fetched again on the next update
                        this.mentionFetches.delete(key);
                        throw error;
                    })
            );
        }
        return this.mentionFetches.get(key);
    }

    /** @param {HTMLAnchorElement} mentionEl */
    unlinkMention(mentionEl) {
        this.unlinkedMentions.add(mentionEl);
        mentionEl.replaceWith(this.document.createTextNode(mentionEl.textContent));
    }

    /**
     * Re-renders the partner mentions whose readonly state is not the expected
     * one: a readonly mention is not a link.
     *
     * @param {(partnerId: number) => { partner: import("models").ResPartner, readonly: boolean }|undefined} getMention
     *  expected state of the mention of the given partner, undefined to keep it as is
     */
    syncPartnerMentions(getMention) {
        let hasChanged = false;
        const elements = this.editable.querySelectorAll(
            ".o_mail_redirect, .o-discuss-readonly-mention"
        );
        for (const el of elements) {
            const mention = getMention(Number(el.dataset.oeId));
            if (mention && mention.readonly === (el.tagName === "A")) {
                el.replaceWith(
                    generatePartnerMentionElement(mention.partner, { readonly: mention.readonly })
                );
                hasChanged = true;
            }
        }
        if (hasChanged) {
            this.dependencies.history.commit();
        }
    }
}
