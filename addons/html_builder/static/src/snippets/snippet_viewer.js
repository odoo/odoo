import { useRef } from "@web/owl2/utils";
import { Component, markup } from "@odoo/owl";
import { useMatrixKeyNavigation } from "@html_builder/utils/keyboard_navigation";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { InputConfirmationDialog } from "./input_confirmation_dialog";
import { fuzzyLevenshteinLookup, fuzzyLookup } from "@web/core/utils/search";
import { selectElements } from "@html_editor/utils/dom_traversal";

export class SnippetViewer extends Component {
    static template = "html_builder.SnippetViewer";
    static props = {
        state: { type: Object },
        selectSnippet: { type: Function },
        hasSearchResults: Function,
        snippetModel: { type: Object },
        installSnippetModule: { type: Function },
        frontendDirection: { type: String },
    };

    setup() {
        this.dialog = useService("dialog");
        this.content = useRef("content");
        this.backendDirection = localization.direction;

        this.handleMatrixKeyNavigation = useMatrixKeyNavigation(
            () => [this.content.el],
            ".o_snippet_preview_wrap"
        );
    }

    /**
     * @typedef {Object} PrefixIconInfo
     * @property {string} keyClass class to add on the span containing the icon
     * @property {string} title the tooltip content
     * @property {Component?} Component the component to show the icon
     * @property {Object?} props props for the component
     * @property {import("@web/core/utils/html").Markup?} content the markup to
     * show the icon, if no `Component`
     */
    /**
     * Gets the info for icons that are shown before the name of the given
     * custom snippet
     *
     * @param {HTMLElement} snippetContentEl
     * @returns {PrefixIconInfo[]}
     */
    getPrefixIcons(snippetContentEl) {
        return [];
    }

    getRenameBtnLabel(snippetName) {
        return _t("Rename %(snippetName)s", { snippetName });
    }
    getDeleteBtnLabel(snippetName) {
        return _t("Delete %(snippetName)s", { snippetName });
    }

    onClickRename(snippet) {
        this.dialog.add(InputConfirmationDialog, {
            title: _t("Rename the block"),
            inputLabel: _t("Name"),
            defaultValue: snippet.title,
            confirmLabel: _t("Save"),
            confirm: (inputValue) => {
                this.props.snippetModel.renameCustomSnippet(snippet, inputValue);
            },
            cancel: () => {},
        });
    }

    onClickDelete(snippet) {
        this.props.snippetModel.deleteCustomSnippet(snippet);
    }

    getSnippetColumns() {
        const snippets = this.getSelectedSnippets();
        const nbColumns = this.props.state.isMobilePreviewMode ? 3 : 2;
        const columns = new Array(nbColumns).fill().map(() => []);

        for (const [index, snippet] of snippets.entries()) {
            columns[index % nbColumns].push(snippet);
        }
        this.props.hasSearchResults(snippets.length > 0);
        return columns;
    }

    onClick(snippet) {
        if (snippet.moduleId) {
            this.props.snippetModel.installSnippetModule(snippet, this.props.installSnippetModule);
        } else {
            this.props.selectSnippet(snippet);
        }
    }

    onPreviewKeydown(ev, snippet) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "enter" || hotkey === "space") {
            this.onClick(snippet);
        }
        this.handleMatrixKeyNavigation(ev);
    }

    getContent(elem) {
        return markup(elem.outerHTML);
    }

    getButtonInstallName(snippet) {
        return _t("Install %s", snippet.title);
    }

    /**
     * Returns the terms used by snippet search: complete labels/classes preserve
     * the regular fuzzy ranking, while split words improve typo matching.
     */
    getSnippetSearchTerms(snippet) {
        const terms = new Set(
            [
                snippet.title || "",
                snippet.name || "",
                snippet.label || "",
                ...(snippet.keyWords?.split(",") || []),
                ...selectElements(snippet.content, "*").flatMap((el) =>
                    [...el.classList].filter((className) => className.startsWith("s_"))
                ),
            ]
                .map((term) => term.trim().toLowerCase())
                .filter((term) => term.length)
        );
        return Array.from(terms);
    }

    getSelectedSnippets() {
        const snippetStructures = this.props.snippetModel.snippetStructures.filter(
            (snippet) => !snippet.isExcluded && !snippet.isDisabled
        );
        if (this.previousSearch !== this.props.state.search) {
            this.previousSearch = this.props.state.search;
            if (this.content.el) {
                this.content.el.ownerDocument.body.scrollTop = 0;
            }
        }
        if (this.props.state.search) {
            const snippetSearchTerms = new Map();
            const getSearchTerms = (snippet) => {
                if (!snippetSearchTerms.has(snippet)) {
                    snippetSearchTerms.set(snippet, this.getSnippetSearchTerms(snippet));
                }
                return snippetSearchTerms.get(snippet);
            };
            const snippets = fuzzyLookup(
                this.props.state.search,
                snippetStructures,
                getSearchTerms
            );
            if (snippets.length) {
                return snippets;
            }
            return snippetStructures.filter(
                (snippet) =>
                    fuzzyLevenshteinLookup(this.props.state.search, getSearchTerms(snippet), 5)
                        .length
            );
        }

        return snippetStructures.filter(
            (snippet) => snippet.groupName === this.props.state.groupSelected
        );
    }
}
