/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import {
    useRef,
    useState,
    useEffect,
    Component,
    onMounted,
} from "@odoo/owl";
import { isBrowserFirefox } from "@web/core/browser/feature_detection";

export class AddSnippetDialog extends Component {
    static template = "web_editor.AddSnippetDialog";
    static props = {
        close: Function,
        snippets: Object,
        groupSelected: String,
        installModule: Function,
        addSnippet: Function,
    };

    static components = {
        Dialog,
    };

    setup() {
        this.title = _t("Insert a block");
        this.snippetGroupTabsRef = useRef("snippetGroupTabs");
        this.iframeRef = useRef("iframe");
        this.snippetGroups = this.getSnippetGroups();
        this.isNavLinkFocused = false;

        this.state = useState({
            groupSelected: [],
        });

        onMounted(async () => {
            const isFirefox = isBrowserFirefox();
            if (isFirefox) {
                // Make sure empty preview iframe is loaded.
                // This event is never triggered on Chrome.
                await new Promise(resolve => {
                    this.iframeDocumentEl.body.onload = resolve;
                });
            }
            this.iframeDocumentEl.body.classList.add("o_add_snippets_preview");
            await this.insertStyle().then(() => {
                this.iframeRef.el.classList.add("show");
            });
            this.state.groupSelected = this.props.groupSelected;
        });

        useEffect(
            () => {
                this.insertSnippets();
            },
            () => [this.state.groupSelected]
        );
    }

    get iframeDocumentEl() {
        return this.iframeRef.el.contentDocument;
    }
    /**
     * Gets snippet groups excluding empty groups.
     *
     * @returns {object} snippets
     */
    getSnippetGroups() {
        return this.props.snippets
            .filter(snippet =>
                (snippet.category.id === "snippet_groups") &&
                snippet.snippetGroup &&
                this.props.snippets.some(snippet => snippet.group === snippet.snippetGroup)
            )
            .map(snippet => ({
                displayName: snippet.displayName,
                name: snippet.snippetGroup,
                selected: snippet.snippetGroup === this.props.groupSelected,
            }));
    }
    /**
     * Inserts the snippets from the selected snippetGroup into the <iframe>.
     */
    async insertSnippets() {
        this.iframeDocumentEl.body.scrollTop = 0;
        this.iframeDocumentEl.body.innerHTML = "";
        const rowEl = document.createElement("div");
        rowEl.classList.add("row", "g-0", "o_snippets_preview_row", "p-5");
        const leftColEl = document.createElement("div");
        leftColEl.classList.add("col-lg-6");
        rowEl.appendChild(leftColEl);
        const rightColEl = document.createElement("div");
        rightColEl.classList.add("col-lg-6");
        rowEl.appendChild(rightColEl);
        this.iframeDocumentEl.body.appendChild(rowEl);

        const snippetsFromSelectedGroup = this.props.snippets
            .filter(snippet => snippet.group === this.state.groupSelected);

        for (const snippet of snippetsFromSelectedGroup) {
            // Create cloned snippet.
            const clonedSnippetEl = snippet.baseBody.cloneNode(true);
            clonedSnippetEl.classList.remove("oe_snippet_body");
            const snippetPreviewWrapEl = document.createElement("div");
            snippetPreviewWrapEl.classList.add("o_snippet_preview_wrap", "m-5", "position-relative", "fade");
            snippetPreviewWrapEl.appendChild(clonedSnippetEl);
            this.__onSnippetPreviewClick = this._onSnippetPreviewClick.bind(this);
            snippetPreviewWrapEl.addEventListener("click", this.__onSnippetPreviewClick);
            // Add an "Install" button for installable snippets.
            if (snippet.installable) {
                clonedSnippetEl.dataset.moduleId = snippet.moduleId;
                const installBtnEl = document.createElement("button");
                installBtnEl.classList.add("o_snippet_preview_install_btn", "btn", "btn-primary", "mx-auto", "bottom-50");
                installBtnEl.innerText = _t("Install");
                snippetPreviewWrapEl.appendChild(installBtnEl);
            }
            // Inserts preview into smallest column.
            const leftColBottom = leftColEl.lastElementChild?.getBoundingClientRect().bottom || 0;
            const rightColBottom = rightColEl.lastElementChild?.getBoundingClientRect().bottom || 0;
            const isLeftColSmallest = leftColBottom <= rightColBottom;
            const lowestColEl = isLeftColSmallest ? leftColEl : rightColEl;
            lowestColEl.appendChild(snippetPreviewWrapEl);
            // Await images.
            const imageEls = snippetPreviewWrapEl.querySelectorAll("img");
            // TODO: move onceAllImagesLoaded in web_editor and to use it here
            await Promise.all(Array.from(imageEls).map(imgEl => {
                imgEl.setAttribute("loading", "eager");
                return new Promise(resolve => {
                    if (imgEl.complete) {
                        resolve();
                    } else {
                        imgEl.onload = () => resolve();
                    }
                });
            }));

            snippetPreviewWrapEl.classList.add("show");
        };

        // Focus active link when the dialog opens.
        const activeLinkEl = this.snippetGroupTabsRef.el.querySelector(".nav-link.active");
        if (!this.isNavLinkFocused && activeLinkEl) {
            activeLinkEl.focus();
            this.isNavLinkFocused = true;
        }
    }
    /**
     * Inserts the style into the iframe's <head>.
     */
    async insertStyle() {
        // Gets the HTML <link> tags of the website preview.
        const pagePreviewIframeEl = document.querySelector(".o_iframe");
        const cssLinkEls = pagePreviewIframeEl.contentDocument.head
            .querySelectorAll("link[type='text/css']");
        // Inserts the the HTML <link> elements into the dialog's <iframe>.
        const linkPromises = Array.from(cssLinkEls).map((cssLinkEl) => {
            return new Promise((resolve) => {
                const clonedLinkEl = cssLinkEl.cloneNode(true);
                this.iframeDocumentEl.head.appendChild(clonedLinkEl);
                clonedLinkEl.onload = () => resolve();
            });
        });
        // If the "Page Layout" option is not "Full" (e.g., "PostCard"), the
        // <main> background color is used to define the "--body-bg" variable so
        // that the snippet previews have the same background color as they
        // would have if dropped into the page.
        const mainEl = pagePreviewIframeEl.contentDocument.body.querySelector("#wrapwrap > main");
        const mainBgColor = mainEl && getComputedStyle(mainEl).backgroundColor;
        if (mainBgColor !== "rgba(0, 0, 0, 0)") {
            this.iframeDocumentEl.body.style.setProperty("--body-bg", mainBgColor);
        }
        await Promise.all(linkPromises);
    }

    _onSnippetPreviewClick(ev) {
        const selectedSnippetEl = ev.currentTarget.querySelector("[data-name]");
        const moduleId = parseInt(selectedSnippetEl.dataset.moduleId);
        if (moduleId) {
            this.props.installModule(moduleId, selectedSnippetEl.dataset.name);
        } else {
            this.props.addSnippet(selectedSnippetEl);
            this.props.close();
        }
    }
}
