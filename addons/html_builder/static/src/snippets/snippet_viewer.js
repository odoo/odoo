import { Component, markup, useRef } from "@odoo/owl";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { InputConfirmationDialog } from "./input_confirmation_dialog";
import { fuzzyLookup } from "@web/core/utils/search";

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
            cancelLabel: _t("Discard"),
            cancel: () => {},
        });
    }

    onClickDelete(snippet) {
        this.props.snippetModel.deleteCustomSnippet(snippet);
    }

    getSnippetColumns() {
        const snippets = this.getSelectedSnippets();

        const columns = [[], []];
        for (const index in snippets) {
            if (index % 2 === 0) {
                columns[0].push(snippets[index]);
            } else {
                columns[1].push(snippets[index]);
            }
        }
        let numResults = 0;
        for (const column of columns) {
            numResults += column.length;
        }
        this.props.hasSearchResults(numResults > 0);
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
    }

    getContent(elem) {
        return markup(elem.outerHTML);
    }

    getButtonInstallName(snippet) {
        return _t("Install %s", snippet.title);
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
        const getClasses = (snippet) => {
            const classes = new Set();
            const elements = [snippet.content, ...snippet.content.querySelectorAll("*")];
            for (const el of elements) {
                for (const className of el.classList) {
                    if (className.startsWith("s_")) {
                        classes.add(className);
                    }
                }
            }
            return Array.from(classes);
        };
        if (this.props.state.search) {
            return fuzzyLookup(this.props.state.search, snippetStructures, (snippet) => [
                snippet.title || "",
                snippet.name || "",
                ...(snippet.keyWords?.split(",") || ""),
                ...getClasses(snippet),
            ]);
        }

        return snippetStructures.filter(
            (snippet) => snippet.groupName === this.props.state.groupSelected
        );
    }
}
