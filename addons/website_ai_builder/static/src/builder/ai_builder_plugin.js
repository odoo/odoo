import { Plugin } from "@html_editor/plugin";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

/**
 * AI Builder Plugin - integrates AI generation with the website editor.
 *
 * Listens for bus notifications sent by the backend AI tools:
 * - "website_ai/apply_html": insert/replace/remove HTML sections in the page
 * - "website_ai/reload_css": save the page and reload CSS bundles after SCSS changes
 */
export class AiBuilderPlugin extends Plugin {
    static id = "aiBuilder";
    static dependencies = ["history", "sanitize", "savePlugin"];
    static shared = ["applyAiHtml", "getPageContext", "getSelectedElementHtml"];

    setup() {
        this.services.bus_service?.subscribe("website_ai/apply_html", (payload) => {
            this.applyAiHtml(payload);
        });
        this.services.bus_service?.subscribe("website_ai/reload_css", () => {
            this._saveAndReloadCSS();
        });
    }

    /**
     * Get the #wrap element or fallback to editable root.
     */
    _getWrapEl() {
        return this.editable.querySelector("#wrap") || this.editable;
    }

    /**
     * Get all top-level sections inside #wrap.
     */
    _getSections() {
        const wrap = this._getWrapEl();
        return [...wrap.querySelectorAll(":scope > section")];
    }

    /**
     * Parse an HTML string into a sanitized DocumentFragment.
     */
    _parseHtml(html) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(`<div>${html}</div>`, "text/html");
        const fragment = this.document.createDocumentFragment();
        for (const child of [...doc.body.firstChild.childNodes]) {
            const imported = this.document.importNode(child, true);
            if (imported.nodeType === Node.ELEMENT_NODE) {
                this.dependencies.sanitize.sanitize(imported);
            }
            fragment.appendChild(imported);
        }
        return fragment;
    }

    /**
     * Apply AI-generated changes to the page.
     *
     * @param {Object} payload
     * @param {string} [payload.html] - HTML content (for append/replace/etc.)
     * @param {string} [payload.action='append'] - edit_content, append, prepend, replace, remove, replace_all
     * @param {number} [payload.sectionIndex] - 1-based section index
     * @param {Array} [payload.contentReplacements] - [{selector, new_inner_html}] for edit_content
     */
    applyAiHtml({ html, action = "append", sectionIndex = null, contentReplacements = null, classOperations = null }) {
        const wrap = this._getWrapEl();
        const sections = this._getSections();

        if (action === "edit_content" && sectionIndex) {
            const target = sections[sectionIndex - 1];
            if (target) {
                if (contentReplacements) {
                    this._applyContentReplacements(target, contentReplacements);
                }
                if (classOperations) {
                    this._applyClassOperations(target, classOperations);
                }
            }
        } else if (action === "remove" && sectionIndex) {
            const target = sections[sectionIndex - 1];
            if (target) {
                target.remove();
            }
        } else if (action === "replace" && sectionIndex) {
            const target = sections[sectionIndex - 1];
            if (target) {
                target.replaceWith(this._parseHtml(html));
            } else {
                wrap.appendChild(this._parseHtml(html));
            }
        } else if (action === "replace_all") {
            for (const section of sections) {
                section.remove();
            }
            wrap.appendChild(this._parseHtml(html));
        } else if (action === "prepend") {
            const firstSection = sections[0];
            if (firstSection) {
                firstSection.before(this._parseHtml(html));
            } else {
                wrap.appendChild(this._parseHtml(html));
            }
        } else {
            // Default: append
            wrap.appendChild(this._parseHtml(html));
        }

        this.dependencies.history.addStep();
    }

    /**
     * Replace innerHTML of targeted elements within a section.
     * Preserves the element itself and surrounding DOM structure,
     * only changing the content inside matched elements.
     *
     * @param {HTMLElement} sectionEl - The section element
     * @param {Array<{selector: string, new_inner_html: string}>} replacements
     */
    _applyContentReplacements(sectionEl, replacements) {
        for (const { selector, new_inner_html: newHtml } of replacements) {
            if (!selector) {
                continue;
            }
            const target = sectionEl.querySelector(selector);
            if (target) {
                // Parse the new HTML through DOMParser to handle entities,
                // then import nodes into the iframe document
                const parser = new DOMParser();
                const doc = parser.parseFromString(`<div>${newHtml}</div>`, "text/html");
                const fragment = this.document.createDocumentFragment();
                for (const child of [...doc.body.firstChild.childNodes]) {
                    fragment.appendChild(this.document.importNode(child, true));
                }
                target.replaceChildren(fragment);
            }
        }
    }

    /**
     * Add or remove CSS classes on targeted elements within a section.
     * When selector is empty, targets the section element itself.
     *
     * @param {HTMLElement} sectionEl - The section element
     * @param {Array<{selector?: string, add?: string, remove?: string}>} operations
     */
    _applyClassOperations(sectionEl, operations) {
        for (const { selector, add, remove } of operations) {
            const target = selector ? sectionEl.querySelector(selector) : sectionEl;
            if (!target) {
                continue;
            }
            if (remove) {
                for (const cls of remove.split(/\s+/).filter(Boolean)) {
                    target.classList.remove(cls);
                }
            }
            if (add) {
                for (const cls of add.split(/\s+/).filter(Boolean)) {
                    target.classList.add(cls);
                }
            }
        }
    }

    /**
     * Save the page, then reload CSS bundles without leaving edit mode.
     */
    async _saveAndReloadCSS() {
        // Save the page so the server sees the latest HTML
        await this.dependencies.savePlugin.save({
            shouldSkipAfterSaveHandlers: async () => true,
        });
        // Reload CSS bundles in the iframe
        const bundles = await rpc("/website/theme_customize_bundle_reload");
        const allOldLinks = [];
        const proms = [];
        for (const [bundleName, bundleURLs] of Object.entries(bundles)) {
            const selector = `link[href*="${bundleName}"]`;
            const oldLinks = this.document.querySelectorAll(selector);
            if (oldLinks.length) {
                allOldLinks.push(...oldLinks);
                const insertionEl = oldLinks[oldLinks.length - 1];
                for (const url of bundleURLs) {
                    const linkEl = this.document.createElement("link");
                    linkEl.setAttribute("type", "text/css");
                    linkEl.setAttribute("rel", "stylesheet");
                    linkEl.setAttribute("href", `${url}#t=${Date.now()}`);
                    proms.push(
                        new Promise((resolve) => {
                            linkEl.addEventListener("load", resolve);
                            linkEl.addEventListener("error", resolve);
                        })
                    );
                    insertionEl.insertAdjacentElement("afterend", linkEl);
                }
            }
        }
        await Promise.all(proms);
        for (const el of allOldLinks) {
            el.remove();
        }
    }

    getPageContext() {
        return this.editable ? this.editable.innerHTML : "";
    }

    getSelectedElementHtml() {
        const activeEl = this.editable.querySelector(".o_active_snippet");
        if (activeEl) {
            return { html: activeEl.outerHTML, element: activeEl };
        }
        const selection = this.document.getSelection();
        if (selection && selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            const container = range.commonAncestorContainer;
            const el = container.nodeType === Node.ELEMENT_NODE
                ? container
                : container.parentElement;
            const section = el?.closest("section[data-snippet]");
            if (section) {
                return { html: section.outerHTML, element: section };
            }
        }
        return null;
    }
}

registry.category("website-plugins").add(AiBuilderPlugin.id, AiBuilderPlugin);
