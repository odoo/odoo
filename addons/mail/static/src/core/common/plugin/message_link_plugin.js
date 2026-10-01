import { Plugin } from "@html_editor/plugin";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { markMessageLink, messageUrlRegExp } from "@mail/utils/common/format";
import { setAttributes } from "@web/core/utils/xml";

const MESSAGE_LINK_SELECTOR = "a.o_message_redirect";
const MESSAGE_LINK_ATTRIBUTES = [
    "contenteditable",
    "data-oe-id",
    "data-oe-model",
    "data-oe-protected",
];

/**
 * Renders the links to messages of this database like in the message body. Only shown: the saved
 * content keeps the URL, as the body is rendered for each reader with their access.
 */
export class MessageLinkPlugin extends Plugin {
    static id = "messageLink";
    static dependencies = ["dom", "domObserver"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        // before the basic composer unwraps the links it does not preserve
        fragment_to_insert_processors: withSequence(5, (fragment) => {
            for (const linkEl of fragment.querySelectorAll(MESSAGE_LINK_SELECTOR)) {
                if (!markMessageLink(linkEl)) {
                    this.unmarkMessageLink(linkEl);
                }
            }
            return fragment;
        }),
        clean_for_save_processors: (root) => {
            for (const linkEl of root.querySelectorAll(MESSAGE_LINK_SELECTOR)) {
                linkEl.classList.remove("o_message_redirect_transformed");
                linkEl.removeAttribute("data-oe-protected");
                linkEl.replaceChildren(linkEl.getAttribute("href"));
            }
            return root;
        },
        // in the insertion step, so that undo removes the whole link
        normalize_processors: (root) => {
            const selector = `a[href*='/mail/message/'], ${MESSAGE_LINK_SELECTOR}`;
            const linkEls = [...root.querySelectorAll(selector)];
            if (root.matches(selector)) {
                linkEls.push(root);
            }
            linkEls.forEach((linkEl) => this.prepareMessageLink(linkEl));
            return root;
        },
        on_content_updated_handlers: () => this.renderMessageLinks(),
        on_editor_started_handlers: () => this.renderMessageLinks(),
        paste_text_overrides: this.handlePasteText.bind(this),
        selectors_for_feff_providers: () => MESSAGE_LINK_SELECTOR,
    };

    /** @type {Map<number, Promise>} */
    messageFetches = new Map();

    /**
     * Pastes a message URL as a link, also where the editor would not (basic composer, localhost).
     *
     * @param {import("@html_editor/core/selection_plugin").EditorSelection} selection
     * @param {string} text
     */
    handlePasteText(selection, text) {
        const url = text.trim();
        // a link can't be in a link, nor in code
        if (!messageUrlRegExp.test(url) || closestElement(selection.anchorNode, "a, code, pre")) {
            return false;
        }
        const linkEl = this.document.createElement("a");
        setAttributes(linkEl, { href: url, rel: "noreferrer noopener", target: "_blank" });
        linkEl.textContent = url;
        markMessageLink(linkEl);
        this.dependencies.dom.insert(linkEl);
        return true;
    }

    /**
     * Marks and renders the link, or unmarks it when it is not to a message of this database.
     *
     * @param {HTMLAnchorElement} linkEl
     */
    prepareMessageLink(linkEl) {
        // a link with its own label is kept, as the message body only renders the URL ones
        if (
            !linkEl.classList.contains("o_message_redirect") &&
            linkEl.textContent.replaceAll("\uFEFF", "").trim() !== linkEl.getAttribute("href")
        ) {
            return;
        }
        if (!markMessageLink(linkEl)) {
            this.unmarkMessageLink(linkEl);
            return;
        }
        for (const [name, value] of Object.entries({
            contenteditable: "false",
            "data-oe-protected": "true",
        })) {
            if (linkEl.getAttribute(name) !== value) {
                linkEl.setAttribute(name, value);
            }
        }
        this.services["mail.store"].renderMessageLinks([linkEl]);
    }

    /** @param {HTMLAnchorElement} linkEl */
    unmarkMessageLink(linkEl) {
        if (!linkEl.classList.contains("o_message_redirect")) {
            return;
        }
        linkEl.classList.remove("o_message_redirect", "o_message_redirect_transformed");
        if (!linkEl.classList.length) {
            linkEl.removeAttribute("class");
        }
        MESSAGE_LINK_ATTRIBUTES.forEach((name) => linkEl.removeAttribute(name));
    }

    /** Not recorded in the history, so that undo never comes back to an unrendered link. */
    renderMessageLinks() {
        const linkEls = [...this.editable.querySelectorAll(MESSAGE_LINK_SELECTOR)];
        if (!linkEls.length) {
            return;
        }
        const store = this.services["mail.store"];
        this.dependencies.domObserver.ignore(() => store.renderMessageLinks(linkEls));
        // only internal users can fetch messages
        if (store.self_user?.share !== false) {
            return;
        }
        for (const messageId of new Set(linkEls.map((el) => Number(el.dataset.oeId)))) {
            if (!store["mail.message"].get(messageId)?.thread?.displayName) {
                this.fetchMessage(messageId);
            }
        }
    }

    /** @param {number} messageId */
    fetchMessage(messageId) {
        if (!this.messageFetches.has(messageId)) {
            this.messageFetches.set(
                messageId,
                this.services["mail.store"]
                    .fetchStoreData("mail.message", { ids: [messageId] })
                    .then(
                        () => !this.isDestroyed && this.renderMessageLinks(),
                        () => {}
                    )
            );
        }
        return this.messageFetches.get(messageId);
    }
}
