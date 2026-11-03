import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { rightPos } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { RECORD_LINK_SELECTOR } from "@mail/core/common/record_link_plugin";
import { getRecordLinkParams, messageUrlRegExp } from "@mail/utils/common/format";
import { setAttributes } from "@web/core/utils/xml";

const RECORD_LINK_ATTRIBUTES = ["contenteditable", "data-oe-id", "data-oe-model"];
const RECORD_LINK_CLASSES = [
    "o_message_redirect",
    "o_message_redirect_transformed",
    "o_record_redirect",
    "o_record_redirect_transformed",
];
const MARKED_RECORD_LINK_SELECTOR =
    "a:is(.o_message_redirect, .o_record_redirect)[data-oe-id]:not(.o_message_redirect_transformed, .o_record_redirect_transformed)";
const RENDERED_RECORD_LINK_SELECTOR =
    "a.o_message_redirect_transformed, a.o_record_redirect_transformed";

/**
 * Class marking the link to a message or a record of this database.
 *
 * @param {string} [url]
 */
function getRecordLinkClass(url) {
    if (messageUrlRegExp.test(url ?? "")) {
        return "o_message_redirect";
    }
    const params = getRecordLinkParams(url);
    if (params) {
        return params.model === "mail.message" ? "o_message_redirect" : "o_record_redirect";
    }
}

/** @param {HTMLAnchorElement} linkEl */
function unmarkRecordLink(linkEl) {
    linkEl.classList.remove(...RECORD_LINK_CLASSES);
    if (!linkEl.classList.length) {
        linkEl.removeAttribute("class");
    }
    RECORD_LINK_ATTRIBUTES.forEach((name) => linkEl.removeAttribute(name));
}

/**
 * Renders the links to messages and records like in the message body. Only shown: the saved
 * content keeps the URL, as the body is rendered for each reader with their access.
 */
export class RecordLinkEditorPlugin extends Plugin {
    static id = "recordLink";
    static dependencies = ["dom", "domObserver", "history", "selection"];
    static shared = ["whenRecordLinksRendered"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        clean_for_save_processors: (root) => {
            for (const linkEl of root.querySelectorAll(RENDERED_RECORD_LINK_SELECTOR)) {
                linkEl.classList.remove(
                    "o_message_redirect_transformed",
                    "o_record_redirect_transformed"
                );
                linkEl.removeAttribute("contenteditable");
                linkEl.replaceChildren(linkEl.getAttribute("href"));
            }
            return root;
        },
        // before the basic composer unwraps the links it does not preserve
        fragment_to_insert_processors: withSequence(5, (fragment) => {
            for (const linkEl of fragment.querySelectorAll(RECORD_LINK_SELECTOR)) {
                const linkClass = getRecordLinkClass(linkEl.getAttribute("href"));
                if (!linkClass || !linkEl.classList.contains(linkClass)) {
                    unmarkRecordLink(linkEl);
                } else if (linkEl.hasAttribute("data-oe-id")) {
                    // rendered again with the access of the user, e.g. copied from a message
                    linkEl.replaceChildren(linkEl.getAttribute("href"));
                }
            }
            return fragment;
        }),
        on_content_updated_handlers: () => this.renderEditedRecordLinks(),
        on_editor_started_handlers: () => this.renderEditedRecordLinks(),
        paste_text_overrides: this.handlePasteText.bind(this),
        // the URLs the html composer pastes as links
        paste_url_overrides: (text) => this.insertRecordLink(text.trim()),
        selectors_for_feff_providers: () => RENDERED_RECORD_LINK_SELECTOR,
    };

    /** @type {Set<Promise>} renders of the pasted links */
    pendingRenders = new Set();

    /**
     * Pastes a message or record URL as a link, also where the editor would not (basic composer,
     * localhost).
     *
     * @param {import("@html_editor/core/selection_plugin").EditorSelection} selection
     * @param {string} text
     */
    handlePasteText(selection, text) {
        // a link can't be in a link, nor in code
        return (
            !closestElement(selection.anchorNode, "a, code, pre") &&
            this.insertRecordLink(text.trim())
        );
    }

    /**
     * Inserts the URL as a link rendered once its record is known. Returns whether it is inserted.
     *
     * @param {string} url
     */
    insertRecordLink(url) {
        const linkClass = getRecordLinkClass(url);
        // a selected text is left to the default paste, e.g. kept as the label of the link in the
        // html composer
        if (!linkClass || !this.dependencies.selection.getEditableSelection().isCollapsed) {
            return false;
        }
        const linkEl = this.document.createElement("a");
        setAttributes(linkEl, {
            class: linkClass,
            href: url,
            rel: "noreferrer noopener",
            target: "_blank",
        });
        linkEl.textContent = url;
        this.dependencies.dom.insert(linkEl);
        const render = this.renderRecordLink(linkEl).finally(() =>
            this.pendingRenders.delete(render)
        );
        this.pendingRenders.add(render);
        return true;
    }

    /** Renders the marked links of the edited message. */
    renderEditedRecordLinks() {
        for (const linkEl of this.editable.querySelectorAll(MARKED_RECORD_LINK_SELECTOR)) {
            this.renderRecordLink(linkEl, { isEdited: true });
        }
    }

    /**
     * @param {HTMLAnchorElement} linkEl
     * @param {{ isEdited?: boolean }} [options]
     */
    async renderRecordLink(linkEl, { isEdited = false } = {}) {
        const href = linkEl.getAttribute("href");
        const recordLink = this.config.composerPluginDependencies.recordLink;
        const record = await recordLink.resolveRecordLink(href);
        if (record) {
            await recordLink.fetchNames(record.model, [record.id]);
        }
        // the link may have been edited or removed meanwhile
        if (
            this.isDestroyed ||
            !this.editable.contains(linkEl) ||
            linkEl.textContent.replaceAll("\uFEFF", "") !== href
        ) {
            return;
        }
        const render = () => {
            const { anchorNode } = this.dependencies.selection.getEditableSelection();
            const hasCaret = linkEl.contains(anchorNode);
            if (!record || !recordLink.renderRecordLink(linkEl, record)) {
                return false;
            }
            setAttributes(linkEl, {
                contenteditable: "false",
                "data-oe-id": record.id,
                "data-oe-model": record.model,
            });
            if (hasCaret) {
                // the text node holding it is replaced
                const [parentEl, offset] = rightPos(linkEl);
                this.dependencies.selection.setSelection({
                    anchorNode: parentEl,
                    anchorOffset: offset,
                });
            }
            return true;
        };
        if (isEdited) {
            // out of the history: undo never turns it back into its URL
            this.dependencies.domObserver.ignore(render);
        } else if (render()) {
            // not protected, in a step of its own: undo turns it back into its URL
            this.dependencies.history.commit();
        } else {
            // marked once posted, e.g. a message the user can't read but its readers may
            this.dependencies.domObserver.ignore(() => unmarkRecordLink(linkEl));
            // not committed, so the content is synced here
            this.config.onChange?.();
        }
    }

    /** Resolved once the pasted links are rendered, which the composer waits for to post. */
    whenRecordLinksRendered() {
        return Promise.allSettled(this.pendingRenders);
    }
}
