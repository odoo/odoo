import { isBrowserFirefox } from "@web/core/browser/feature_detection";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import {
    useRef,
    useState,
    useEffect,
    Component,
    onMounted,
} from "@odoo/owl";
import { localization } from "@web/core/l10n/localization";

export class RenameCustomSnippetDialog extends Component {
    static template = "web_editor.RenameCustomSnippetDialog";
    static props = {
        close: Function,
        currentName: String,
        confirm: Function,
    };

    static components = {
        Dialog,
    };
    setup() {
        this.renameInputRef = useRef("renameInput");
    }
    onClickConfirm() {
        this.props.confirm(this.renameInputRef.el.value);
        this.props.close();
    }
    onClickDiscard() {
        this.props.close();
    }
}
export class AddSnippetDialog extends Component {
    static template = "web_editor.AddSnippetDialog";
    static props = {
        close: Function,
        snippets: Object,
        groupSelected: String,
        optionsSnippets: String,
        frontendDirection: String,
        installModule: Function,
        addSnippet: Function,
        deleteCustomSnippet: Function,
        renameCustomSnippet: Function,
    };

    static components = {
        Dialog,
        RenameCustomSnippetDialog,
    };

    setup() {
        this.iframeRef = useRef("iframe");
        this.snippetGroups = this.getSnippetGroups();

        this.dialog = useService("dialog");

        this.state = useState({
            groupSelected: [],
            search: "",
        });

        onMounted(async () => {
            const isFirefox = isBrowserFirefox();
            if (isFirefox) {
                // Make sure empty preview iframe is loaded.
                // This event is never triggered on Chrome.
                await new Promise(resolve => {
                    this.iframeDocument.body.onload = resolve;
                });
            }
            this.iframeDocument.documentElement.classList.add("o_add_snippets_preview");
            this.iframeDocument.body.style.setProperty("direction", localization.direction);
            await this.insertStyle().then(() => {
                this.iframeRef.el.classList.add("show");
            });
            this.state.groupSelected = this.props.groupSelected;
        });

        this.currentInsertSnippetsCallID = 0;
        useEffect(
            () => {
                this.insertSnippets();
            },
            () => [this.state.groupSelected, this.state.search, [...this.props.snippets]]
        );
    }

    get iframeDocument() {
        return this.iframeRef.el.contentDocument;
    }
    /**
     * Gets snippet groups.
     *
     * @returns {object} snippets
     */
    getSnippetGroups() {
        return [...this.props.snippets.values()]
            .filter(snippet =>
                !snippet.excluded
                && (snippet.category.id === "snippet_groups")
                && snippet.snippetGroup
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
        const insertSnippetsCallID = ++this.currentInsertSnippetsCallID;

        // First, filter out snippets which are never supposed to be shown
        // (excluded ones, inner content ones, ...).
        let snippetsToDisplay = [...this.props.snippets.values()].filter(snippet => {
            // Note: custom ones have "custom" group, but inner ones (custom or
            // not) have no group.
            return !snippet.excluded && snippet.group;
        });

        if (this.state.search) {
            const search = this.state.search;
            const selectorSearch = /^s_[\w-]*$/.test(search) && `[class^="${search}"], [class*=" ${search}"]`;
            const lowerCasedSearch = search.toLowerCase();
            const strMatches = str => str.toLowerCase().includes(lowerCasedSearch);
            snippetsToDisplay = snippetsToDisplay.filter(snippet => {
                return selectorSearch && (
                        snippet.baseBody.matches(selectorSearch)
                        || snippet.baseBody.querySelector(selectorSearch)
                    )
                    || strMatches(snippet.category.text)
                    || strMatches(snippet.displayName)
                    || strMatches(snippet.data.oeKeywords || '');
            });
            // Make sure to show the snippets that "better" match first
            if (selectorSearch) {
                snippetsToDisplay.sort((snippetA, snippetB) => {
                    // If the search is exactly equal to a snippet xmlid, show
                    // that snippet first.
                    if (snippetA.data.snippet === search) {
                        return -1;
                    }
                    if (snippetB.data.snippet === search) {
                        return 1;
                    }

                    // If the search is a full class name used on the snippet
                    // root node, show that snippet first.
                    const aHasExactClassOnRoot = snippetA.baseBody.classList.contains(search);
                    const bHasExactClassOnRoot = snippetB.baseBody.classList.contains(search);
                    if (aHasExactClassOnRoot !== bHasExactClassOnRoot) {
                        return aHasExactClassOnRoot ? -1 : 1;
                    }

                    // Otherwise show a partial class match of a snippet first
                    // if it happens on the root node.
                    const aHasPartialClassOnRoot = snippetA.baseBody.matches(selectorSearch);
                    const bHasPartialClassOnRoot = snippetB.baseBody.matches(selectorSearch);
                    if (aHasPartialClassOnRoot !== bHasPartialClassOnRoot) {
                        return aHasPartialClassOnRoot ? -1 : 1;
                    }

                    return 0;
                });
            }
        } else {
            // No search: display the currently selected tab (group)
            snippetsToDisplay = snippetsToDisplay.filter(snippet => {
                return snippet.group === this.state.groupSelected;
            });
        }

        if (!snippetsToDisplay.length && this.state.groupSelected === "custom") {
            this.snippetGroups = this.snippetGroups.filter(group => group.name !== "custom");
            this.state.groupSelected = this.snippetGroups[0].name;
            return;
        }

        // Create the new 2-column structure
        this.iframeDocument.body.scrollTop = 0;
        const rowEl = document.createElement("div");
        rowEl.classList.add("row", "g-0", "o_snippets_preview_row");
        rowEl.style.setProperty("direction", this.props.frontendDirection);
        const leftColEl = document.createElement("div");
        leftColEl.classList.add("col-lg-6");
        rowEl.appendChild(leftColEl);
        const rightColEl = document.createElement("div");
        rightColEl.classList.add("col-lg-6");
        rowEl.appendChild(rightColEl);
        this.iframeDocument.body.appendChild(rowEl);

        // Split the next computation in chunks. A first big chunk of snippets
        // to be computed first, then the rest in smaller chunks. This allows to
        // make sure that a tab with many snippets (or a one letter search for
        // instance) can show something filling the screen quickly without a
        // laggy effect, and without waiting for the full computation. Splitting
        // the rest in smaller chunks allow to cancel the loading quickly if a
        // new search is entered.
        const BIG_CHUNK_SIZE = 6;
        const SMALL_CHUNK_SIZE = 3;
        const chunks = [snippetsToDisplay.splice(0, BIG_CHUNK_SIZE)];
        while (snippetsToDisplay.length) {
            chunks.push(snippetsToDisplay.splice(0, SMALL_CHUNK_SIZE));
        }
        let leftColSize = 0;
        let rightColSize = 0;
        for (const chunk of chunks) {
            // First compute all snippets UI and put them in the left column,
            // invisible. Parallelize image loading and wait for it before
            // sorting the items in the right column.
            const itemEls = await Promise.all(chunk.map(snippet => {
                let containerEl = null;

                // Create cloned snippet.
                let clonedSnippetEl;
                let originalSnippet;
                if (snippet.isCustom) {
                    originalSnippet = [...this.props.snippets.values()].filter(snip =>
                        !snip.isCustom && snip.name === snippet.name
                    )[0];
                    if (originalSnippet.baseBody.querySelector(".s_dialog_preview")
                        || originalSnippet.imagePreview
                        // Specific case for "s_countdown" because it's hybrid (also
                        // inner content). TODO: It might be possible to have a real
                        // preview for "s_countdown".
                        || originalSnippet.name === "s_countdown") {
                        clonedSnippetEl = originalSnippet.baseBody.cloneNode(true);
                    }
                }
                if (!clonedSnippetEl) {
                    clonedSnippetEl = snippet.baseBody.cloneNode(true);
                }
                clonedSnippetEl.classList.remove("oe_snippet_body");
                const snippetPreviewWrapEl = document.createElement("div");
                snippetPreviewWrapEl.classList.add("o_snippet_preview_wrap", "position-relative");
                snippetPreviewWrapEl.dataset.snippetId = snippet.name;
                snippetPreviewWrapEl.dataset.snippetKey = snippet.key;
                snippetPreviewWrapEl.appendChild(clonedSnippetEl);
                this.__onSnippetPreviewClick = this._onSnippetPreviewClick.bind(this);
                snippetPreviewWrapEl.addEventListener("click", this.__onSnippetPreviewClick);
                containerEl = snippetPreviewWrapEl;

                // Add an "Install" button for installable snippets.
                if (snippet.installable) {
                    snippetPreviewWrapEl.classList.add("o_snippet_preview_install");
                    clonedSnippetEl.dataset.moduleId = snippet.moduleId;
                    const installBtnEl = document.createElement("button");
                    installBtnEl.classList.add("o_snippet_preview_install_btn", "btn", "text-white", "rounded-1", "mx-auto", "p-2", "bottom-50");
                    installBtnEl.innerText = _t("Install %s", snippet.displayName);
                    snippetPreviewWrapEl.appendChild(installBtnEl);
                }

                // Replace the snippet with an image preview if one exists.
                const imagePreview = snippet.imagePreview || originalSnippet?.imagePreview;
                if (imagePreview) {
                    // Enforce no-padding for image previews
                    clonedSnippetEl.style.setProperty("padding", "0", "important");
                    const previewImgDivEl = document.createElement("div");
                    previewImgDivEl.classList.add("s_dialog_preview", "s_dialog_preview_image");
                    const previewImgEl = document.createElement("img");
                    previewImgEl.src = imagePreview;
                    previewImgDivEl.appendChild(previewImgEl);
                    clonedSnippetEl.innerHTML = "";
                    clonedSnippetEl.appendChild(previewImgDivEl);
                }

                clonedSnippetEl.classList.remove("o_dynamic_empty");

                // Custom snippet.
                if (snippet.isCustom) {
                    const editCustomSnippetEl = document.createElement("div");
                    editCustomSnippetEl.classList.add("d-grid", "mt-2", "mx-5", "gap-2",
                        "d-md-flex", "justify-content-md-end", "o_custom_snippet_edit");

                    const spanEl = document.createElement("span");
                    spanEl.classList.add("w-100");
                    spanEl.textContent = snippet.displayName;

                    const renameBtnEl = document.createElement("button");
                    renameBtnEl.classList.add("btn", "fa", "fa-pencil", "me-md-2");
                    renameBtnEl.type = "button";

                    const removeBtnEl = document.createElement("button");
                    removeBtnEl.classList.add("btn", "fa", "fa-trash");
                    removeBtnEl.type = "button";

                    editCustomSnippetEl.appendChild(spanEl);
                    editCustomSnippetEl.appendChild(renameBtnEl);
                    editCustomSnippetEl.appendChild(removeBtnEl);

                    const customSnippetWrapEl = document.createElement("div");
                    customSnippetWrapEl.classList.add("o_custom_snippet_wrap");
                    customSnippetWrapEl.appendChild(snippetPreviewWrapEl);
                    customSnippetWrapEl.appendChild(editCustomSnippetEl);
                    containerEl = customSnippetWrapEl;

                    this.__onRenameCustomBtnClick = this._onRenameCustomBtnClick.bind(this);
                    renameBtnEl.addEventListener("click", this.__onRenameCustomBtnClick);
                    this.__onDeleteCustomBtnClick = this._onDeleteCustomBtnClick.bind(this);
                    removeBtnEl.addEventListener("click", this.__onDeleteCustomBtnClick);
                }

                // Will be sorted in the right columns after
                containerEl.classList.add("invisible");
                leftColEl.appendChild(containerEl);

                // Await images.
                const imageEls = snippetPreviewWrapEl.querySelectorAll("img");
                // TODO: move onceAllImagesLoaded in web_editor and to use it here
                return Promise.all(Array.from(imageEls).map(imgEl => {
                    imgEl.setAttribute("loading", "eager");
                    return new Promise(resolve => {
                        if (imgEl.complete) {
                            resolve();
                        } else {
                            imgEl.onload = () => resolve();
                            // If the image could not be loaded, we still want the
                            // "d-none" class to be removed.
                            imgEl.onerror = () => resolve();
                        }
                    });
                })).then(() => containerEl);
            }));

            // During the asynchronous period, another call to insertSnippets
            // could have been made. In that case, we should just stop here.
            if (this.currentInsertSnippetsCallID !== insertSnippetsCallID) {
                return;
            }

            // Sort items in the right column based on their size and the
            // currently computed size of the column. Note that this does not
            // compute the size of the column after each element addition: this
            // is wildly inefficient. Instead: compute the sizes, then add them
            // all in one go into the right column.
            const leftColElements = [];
            const rightColElements = [];
            for (const itemEl of itemEls) {
                const size = itemEl.getBoundingClientRect().height;
                if (leftColSize <= rightColSize) {
                    leftColElements.push(itemEl);
                    leftColSize += size;
                } else {
                    rightColElements.push(itemEl);
                    rightColSize += size;
                }
            }
            for (const [colEl, colItemEls] of [
                [leftColEl, leftColElements],
                [rightColEl, rightColElements],
            ]) {
                for (const el of colItemEls) {
                    colEl.appendChild(el);
                    el.classList.remove("invisible");
                }
            }

            // Only when the first chunk is loaded do we remove the previously
            // loaded search.
            while (rowEl.previousSibling) {
                rowEl.previousSibling.remove();
            }
        }

        this._updateSnippetContent(this.iframeDocument);
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
                this.iframeDocument.head.appendChild(clonedLinkEl);
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
            this.iframeDocument.body.style.setProperty("--body-bg", mainBgColor);
        }
        await Promise.all(linkPromises);
    }

    _onSnippetPreviewClick(ev) {
        let selectedSnippetEl = ev.currentTarget.querySelector("[data-name]");
        const snippetKey = parseInt(ev.currentTarget.dataset.snippetKey);
        const moduleId = parseInt(selectedSnippetEl?.dataset.moduleId);
        if (moduleId) {
            this.props.installModule(moduleId, selectedSnippetEl.dataset.name);
        } else {
            selectedSnippetEl = this.props.snippets.get(snippetKey);
            selectedSnippetEl = selectedSnippetEl.baseBody.cloneNode(true);
            selectedSnippetEl.classList.remove("oe_snippet_body");
            const snippetDialogPreviews = selectedSnippetEl.querySelectorAll(".s_dialog_preview");
            for (const snippetDialogPreview of snippetDialogPreviews) {
                snippetDialogPreview.remove();
            }
            this.props.addSnippet(selectedSnippetEl);
            // Adapt the snippet content right after adding it to the DOM.
            this._updateSnippetContent(selectedSnippetEl);
            this.props.close();
        }
    }

    _onRenameCustomBtnClick(ev) {
        const snippetKey = ev.currentTarget.closest(".o_custom_snippet_wrap")
            .querySelector("[data-snippet-key]").dataset.snippetKey;
        const snippet = this.props.snippets.get(parseInt(snippetKey));
        this.dialog.add(RenameCustomSnippetDialog, {
            currentName: snippet.displayName,
            confirm: async (newName) => {
                this.props.renameCustomSnippet(parseInt(snippetKey), newName);
            },
        });
    }

    _onDeleteCustomBtnClick(ev) {
        const snippetKey = ev.currentTarget.closest(".o_custom_snippet_wrap")
            .querySelector("[data-snippet-key]").dataset.snippetKey;
        this.props.deleteCustomSnippet(parseInt(snippetKey));
    }

    /**
     * Allows to update the snippets to build & adapt dynamic content.
     *
     * @private
     */
    _updateSnippetContent(snippetEl) {}
}
