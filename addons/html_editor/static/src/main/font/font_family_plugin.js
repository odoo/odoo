import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { FontFamilySelector } from "@html_editor/main/font/font_family_selector";
import { reactive } from "@odoo/owl";
import { closestElement } from "../../utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";

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
    static dependencies = ["split", "selection", "dom", "format", "font"];
    fontFamily = reactive({ displayName: defaultFontFamily.nameShort });
    /** @type {import("plugins").EditorResources} */
    resources = {
        toolbar_items: [
            withSequence(15, {
                id: "font-family",
                groupId: "font",
                description: _t("Select font family"),
                Component: FontFamilySelector,
                props: {
                    fontFamilyItems: fontFamilyItems,
                    currentFontFamily: this.fontFamily,
                    onSelected: (item) => {
                        this.dependencies.format.formatSelection("fontFamily", {
                            applyStyle: item.fontFamily !== false,
                            formatProps: item,
                        });
                        this.fontFamily.displayName = item.nameShort;
                    },
                },
                isAvailable: (selection) =>
                    isHtmlContentSupported(selection) && (this.config.allowFontFamily ?? true),
            }),
        ],
        /** Handlers */
        selectionchange_handlers: this.updateCurrentFontFamily.bind(this),
        post_undo_handlers: this.updateCurrentFontFamily.bind(this),
        post_redo_handlers: this.updateCurrentFontFamily.bind(this),
    };

    updateCurrentFontFamily(ev) {
        const selelectionData = this.dependencies.selection.getSelectionData();
        if (!selelectionData.documentSelectionIsInEditable) {
            return;
        }
        const anchorElement = closestElement(selelectionData.editableSelection.anchorNode);
        const anchorElementFontFamily = getComputedStyle(anchorElement).fontFamily;
        const currentFontItem =
            anchorElementFontFamily &&
            fontFamilyItems.find((item) => item.fontFamily === anchorElementFontFamily);

        this.fontFamily.displayName = (currentFontItem || defaultFontFamily).nameShort;
    }
}
