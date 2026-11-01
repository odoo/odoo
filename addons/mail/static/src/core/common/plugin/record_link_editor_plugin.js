import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { getRecordLinkParams } from "@mail/utils/common/format";
import { setAttributes } from "@web/core/utils/xml";

const MARKED_RECORD_LINK_SELECTOR = "a.o_record_redirect[data-oe-id]";
const RENDERED_RECORD_LINK_SELECTOR = "a.o_record_redirect_transformed";

/**
 * Renders the links to records like in the message body. Only shown: the saved content keeps the
 * URL, as the body is rendered for each reader with their access.
 */
export class RecordLinkEditorPlugin extends Plugin {
    static id = "recordLink";
    static dependencies = ["dom", "domObserver", "history"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        clean_for_save_processors: (root) => {
            for (const linkEl of root.querySelectorAll(RENDERED_RECORD_LINK_SELECTOR)) {
                linkEl.classList.remove("o_record_redirect_transformed");
                linkEl.removeAttribute("contenteditable");
                linkEl.replaceChildren(linkEl.getAttribute("href"));
            }
            return root;
        },
        on_editor_started_handlers: () => this.renderEditedRecordLinks(),
        paste_text_overrides: this.handlePasteText.bind(this),
        // the URLs the html composer pastes as links
        paste_url_overrides: (text) => this.insertRecordLink(text.trim()),
        selectors_for_feff_providers: () => RENDERED_RECORD_LINK_SELECTOR,
    };

    /**
     * Pastes a record URL as a link, also where the editor would not (basic composer, localhost).
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
        if (!getRecordLinkParams(url)) {
            return false;
        }
        const linkEl = this.document.createElement("a");
        setAttributes(linkEl, {
            class: "o_record_redirect",
            href: url,
            rel: "noreferrer noopener",
            target: "_blank",
        });
        linkEl.textContent = url;
        this.dependencies.dom.insert(linkEl);
        this.renderRecordLink(linkEl);
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
        if (!record) {
            return;
        }
        await recordLink.fetchNames(record.model, [record.id]);
        // the link may have been edited or removed meanwhile
        if (
            this.isDestroyed ||
            !this.editable.contains(linkEl) ||
            linkEl.textContent.replaceAll("﻿", "") !== href
        ) {
            return;
        }
        const render = () => {
            if (!recordLink.renderRecordLink(linkEl, record)) {
                return false;
            }
            setAttributes(linkEl, {
                contenteditable: "false",
                "data-oe-id": record.id,
                "data-oe-model": record.model,
            });
            return true;
        };
        if (isEdited) {
            // out of the history: undo never turns it back into its URL
            this.dependencies.domObserver.ignore(render);
        } else if (render()) {
            // not protected, in a step of its own: undo turns it back into its URL
            this.dependencies.history.commit();
        }
    }
}
