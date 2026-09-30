import { proxy } from "@odoo/owl";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { FontFamilySelector } from "@html_editor/main/font/font_family_selector";
import { closestElement } from "../../utils/dom_traversal";
import { removeStyle } from "@html_editor/utils/formatting";
import { READ, withSequence } from "@html_editor/utils/resource";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { isStylable } from "@html_editor/utils/dom_info";

export const defaultFontFamily = {
    name: "Default system font",
    nameShort: "Default font",
    fontFamily: false,
};
export const fontFamilyItems = [
    defaultFontFamily,
    { name: "Arial (sans-serif)", nameShort: "Arial", fontFamily: "Arial, sans-serif" },
    { name: "Verdana (sans-serif)", nameShort: "Verdana", fontFamily: "Verdana, sans-serif" },
    { name: "Tahoma (sans-serif)", nameShort: "Tahoma", fontFamily: "Tahoma, sans-serif" },
    {
        name: "Trebuchet MS (sans-serif)",
        nameShort: "Trebuchet MS",
        fontFamily: '"Trebuchet MS", sans-serif',
    },
    {
        name: "Courier New (monospace)",
        nameShort: "Courier New",
        fontFamily: '"Courier New", monospace',
    },
];

export class FontFamilyPlugin extends Plugin {
    static id = "fontFamily";
    static dependencies = ["split", "selection", "dom", "format"];
    fontFamily = proxy({ displayName: defaultFontFamily.nameShort });
    /** @type {import("plugins").EditorResources} */
    resources = {
        format_specs: [
            {
                id: "fontFamily",
                isFormatted: (node) => !!closestElement(node, (el) => el.style["font-family"]),
                hasStyle: (node) => node.style && node.style["font-family"],
                getFormatProps: (node) => {
                    if (node.style?.["font-family"]) {
                        return { fontFamily: node.style["font-family"] };
                    }
                },
                addStyle: (node, props) => {
                    removeStyle(node, "font-family");
                    if (props.fontFamily) {
                        node.style["font-family"] = props.fontFamily;
                    }
                },
                removeStyle: (node) => removeStyle(node, "font-family"),
            },
        ],
        toolbar_items: [
            withSequence(15, {
                id: "font-family",
                groupId: "font",
                description: _t("Select font family"),
                Component: FontFamilySelector,
                props: {
                    fontFamilyItems: fontFamilyItems,
                    currentFontFamily: this.fontFamily,
                    focusEditable: () => this.dependencies.selection.focusEditable(),
                    onSelected: (item) => {
                        this.dependencies.format.requestFormat("fontFamily", {
                            applyStyle: item.fontFamily !== false,
                            formatProps: item,
                        });
                        this.updateCurrentFontFamily();
                    },
                },
                isDisabled: (sel, nodes) => nodes.some((node) => !isStylable(node)),
                isAvailable: (selection) =>
                    isHtmlContentSupported(selection) && (this.config.allowFontFamily ?? true),
            }),
        ],
        /** Handlers */
        on_selectionchange_handlers: withSequence(READ, this.updateCurrentFontFamily.bind(this)),
        on_history_commit_undone_handlers: this.updateCurrentFontFamily.bind(this),
        on_history_commit_redone_handlers: this.updateCurrentFontFamily.bind(this),
        on_collapsed_formats_removed_handlers: this.updateCurrentFontFamily.bind(this),
    };

    updateCurrentFontFamily(ev) {
        const pendingIntent = this.dependencies.format.getPendingIntents()["fontFamily"];
        let currentFontFamily = pendingIntent?.applyStyle && pendingIntent.formatProps?.fontFamily;
        if (!currentFontFamily) {
            const selectionData = this.dependencies.selection.getSelectionData();
            if (!selectionData.documentSelectionIsInEditable) {
                return;
            }

            const anchorElement = closestElement(selectionData.editableSelection.anchorNode);
            currentFontFamily = getComputedStyle(anchorElement).fontFamily;
        }
        const currentFontItem =
            currentFontFamily &&
            fontFamilyItems.find((item) => item.fontFamily === currentFontFamily);

        this.fontFamily.displayName = (currentFontItem || defaultFontFamily).nameShort;
    }
}
