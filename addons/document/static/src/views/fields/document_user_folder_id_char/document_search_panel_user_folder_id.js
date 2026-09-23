/** @odoo-module native */
import { useService } from "@web/core/utils/hooks";
import { fuzzyTest } from "@web/core/utils/search";
import { toFolderValueId } from "@document/views/utils";

import { DocumentsSearchPanel } from "@document/views/search/document_search_panel";

import { Component, onWillStart, useRef, useState } from "@odoo/owl";

export class DocumentsSearchPanelUserFolderId extends Component {
    static excludedValues = ["RECENT", "TRASH"];
    static template = "document.SearchPanelUserFolderId";
    static subTemplates = {
        category: "document.SearchPanel.Category",
    };
    static rootIcons = DocumentsSearchPanel.rootIcons;
    static props = {
        value: { type: String, optional: false },
        onChange: { type: Function, optional: false },
        ulClass: { type: String, optional: true },
    };
    setup() {
        this.orm = useService("orm");
        const activeValueId = toFolderValueId(this.props.value);
        this.state = useState({
            active: { 1: activeValueId },
            expanded: { 1: {} },
        });
        this.category = useState({
            activeValueId,
            description: "Folders",
            icon: "fa-folder",
            id: 1,
            rootIds: [false],
            values: new Map([
                [
                    false,
                    {
                        childrenIds: [],
                        display_name: "All",
                        id: false,
                        bold: true,
                        parentId: false,
                    },
                ],
            ]),
        });
        this._treeValues = [];
        this.inputRef = useRef("searchInput");

        onWillStart(async () => {
            const result = await this.orm.call(
                "document.document",
                "search_panel_select_range",
                ["user_folder_id"],
                {},
            );
            const values = result.values
                .filter((v) => !this.constructor.excludedValues.includes(v.id))
                .sort((a, b) => (a.id === "MY" ? -1 : b.id === "MY" ? 1 : 0));
            this._treeValues = values;
            this._createCategoryTree({ values, initialValue: activeValueId });
        });
    }

    get ulClass() {
        return this.props.ulClass || "";
    }

    isUploadingInFolder() {
        return false;
    }

    async toggleCategory(category, value) {
        const newActiveValueId = value.id;
        if (category.activeValueId !== newActiveValueId) {
            this.props.onChange(newActiveValueId.toString(), value);
            category.activeValueId = newActiveValueId;
            this.state.active[1] = newActiveValueId;
        }
    }

    async toggleFold(category, value) {
        const categoryState = this.state.expanded[category.id];
        categoryState[value.id] = !categoryState[value.id];
    }

    /**
     * @param {Object} category
     * @param {Object} value
     * @returns {string|false}
     */
    categoryAriaExpanded(category, value) {
        if (!value.childrenIds.length) {
            return false;
        }
        return this.state.expanded[category.id][value.id] ? "true" : "false";
    }

    onFilterChange(ev) {
        const query = ev.target.value;
        this._createCategoryTree({ values: this._treeValues, query });
    }

    onClickClear() {
        this.inputRef.el.value = "";
        this.inputRef.el.dispatchEvent(
            new CustomEvent("change", { detail: { value: "" } }),
        );
    }

    /**
     * @param { Object[] } values
     * @param { String? } query
     * @param { Number } initialValue
     */
    _createCategoryTree({ values, query, initialValue }) {
        const category = this.category;
        const lowercaseQuery = query?.toLowerCase();
        const newCategoryValues = new Map();
        for (const value of values) {
            const parentId = value["user_folder_id"] || false;
            newCategoryValues.set(
                value.id,
                Object.assign({}, value, {
                    parentId,
                    childrenIds: [],
                }),
            );
        }

        for (const [id, node] of newCategoryValues.entries()) {
            const parentId = node.parentId;
            if (parentId && newCategoryValues.has(parentId)) {
                newCategoryValues.get(parentId).childrenIds.push(id);
            }
        }

        let idsToInclude = new Set(newCategoryValues.keys());
        const newExpanded = {};

        if (lowercaseQuery) {
            const matchingIds = new Set();
            for (const [id, node] of newCategoryValues.entries()) {
                if (!node.parentId && !node.user_folder_id) {
                    continue;
                }
                if (node.display_name && fuzzyTest(lowercaseQuery, node.display_name)) {
                    matchingIds.add(id);
                }
            }

            const relevantIds = new Set(matchingIds);

            for (const id of matchingIds) {
                let current = newCategoryValues.get(id);
                while (current?.parentId && newCategoryValues.has(current.parentId)) {
                    const parentId = current.parentId;
                    relevantIds.add(parentId);
                    newExpanded[parentId] = true;
                    current = newCategoryValues.get(parentId);
                }
            }

            const collectDescendants = (id) => {
                const node = newCategoryValues.get(id);
                if (!node) {
                    return;
                }
                for (const childId of node.childrenIds) {
                    if (!relevantIds.has(childId)) {
                        relevantIds.add(childId);
                        collectDescendants(childId);
                    }
                }
            };
            for (const id of matchingIds) {
                collectDescendants(id);
            }

            for (const [id, node] of newCategoryValues.entries()) {
                if (!node.parentId) {
                    relevantIds.add(id);
                }
            }
            idsToInclude = relevantIds;
        } else {
            for (const [id, node] of newCategoryValues.entries()) {
                if (!node.parentId) {
                    newExpanded[id] = true;
                }
            }
            const ancestors = this.getFolderAndParents(newCategoryValues, initialValue);
            for (const folder of ancestors) {
                if (!newExpanded[folder.id]) {
                    newExpanded[folder.id] = true;
                }
            }
        }

        this.state.expanded[1] = newExpanded;

        this._setCategoryValues(category, idsToInclude, newCategoryValues);

        category.rootIds = [false];
        for (const [id, node] of category.values.entries()) {
            if (!node.parentId || !category.values.has(node.parentId)) {
                category.rootIds.push(id);
            }
        }
    }

    _setCategoryValues(category, idsToInclude, categoryMap) {
        for (const folderId of category.values.keys()) {
            if (typeof folderId === "number") {
                category.values.delete(folderId);
            }
        }
        for (const id of idsToInclude) {
            if (categoryMap.has(id)) {
                const node = Object.assign({}, categoryMap.get(id), {
                    childrenIds: [],
                });
                category.values.set(id, node);
            }
        }
        for (const [id, node] of category.values.entries()) {
            const parentId = node.parentId;
            if (parentId && category.values.has(parentId)) {
                category.values.get(parentId).childrenIds.push(id);
            }
        }
    }

    getFolderAndParents(categoryValues, initialValue) {
        let folder = categoryValues.get(initialValue);
        const folders = [];
        while (folder) {
            folders.push(folder);
            folder = folder.folder_id
                ? categoryValues.get(folder.folder_id)
                : categoryValues.get(folder.user_folder_id);
        }
        return folders;
    }
}
