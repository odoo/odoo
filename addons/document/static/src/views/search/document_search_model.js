/** @odoo-module native */
import { useSetupAction } from "@web/core/action_hook";
import { SearchModel } from "@web/search/search_model";
import { browser } from "@web/core/browser/browser";
import { router } from "@web/core/browser/router";
import { Domain } from "@web/core/domain";
import { useService } from "@web/core/utils/hooks";
import { toFolderValueId } from "@document/views/utils";

export class DocumentsSearchModel extends SearchModel {
    setup(services) {
        super.setup(services);
        this.documentService = useService("document.document");
        this.orm = useService("orm");
        this.skipLoadClosePreview = false;
        useSetupAction({
            beforeLeave: () => {
                this._updateRouteState({ user_folder_id: undefined });
            },
        });
    }

    /**
     * @returns {Object|undefined}
     */
    get folderCategory() {
        return this.categories.find((cat) => cat.fieldName === "user_folder_id");
    }

    async load(config) {
        if (
            this.documentService.initData.documentId ||
            config.context.documents_init_document_id
        ) {
            config.irFilters.forEach((fil) => {
                fil.is_default = false;
            });
            for (const key in config.context) {
                const searchDefaultMatch = /^search_default_(.*)$/.exec(key);
                if (searchDefaultMatch) {
                    delete config.context[key];
                }
                if (key === "documents_init_document_id") {
                    this.documentService.documentIdToRestoreOnce =
                        config.context.documents_init_document_id;
                    delete config.context[key];
                }
            }
        }

        await super.load(config);

        let folderId = router.current.user_folder_id || this.getSelectedFolderId();

        if (folderId) {
            if (!this.getFolderById(folderId)) {
                folderId = false;
            }
            this.toggleCategoryValue(this.folderCategory.id, folderId);
        }
    }

    /**
     * @override
     */
    _createCategoryTree(sectionId) {
        const category = this.sections.get(sectionId);
        super._createCategoryTree(...arguments);
        const findRootId = (folder) => {
            if (!folder.parentId) {
                return folder.id;
            }
            const parent = category.values.get(folder.parentId);
            if (!parent) {
                return false;
            }
            if (parent.rootId !== undefined) {
                return parent.rootId;
            } else {
                const rootId = findRootId(parent);
                parent.rootId = rootId;
                return rootId;
            }
        };
        for (const [, folder] of category.values) {
            if (!folder.rootId) {
                folder.rootId = findRootId(folder);
            }
        }
    }

    /**
     * @override
     */
    takeSearchDefaultsFromGlobalContext() {
        const { searchDefaults, searchPanelDefaults } =
            super.takeSearchDefaultsFromGlobalContext(...arguments);
        if (searchPanelDefaults.user_folder_id) {
            searchPanelDefaults.user_folder_id = toFolderValueId(
                searchPanelDefaults.user_folder_id,
            );
            if (!this.globalContext.no_documents_unique_folder_id) {
                this.globalContext["documents_unique_folder_id"] =
                    searchPanelDefaults.user_folder_id;
            }
        }
        return { searchDefaults, searchPanelDefaults };
    }

    /**
     * @returns {Object[]}
     */
    getFolders() {
        return [...(this.folderCategory?.values.values() ?? [])];
    }

    /**
     * @returns {Object | false}
     */
    getFolderById(folderId) {
        return this.folderCategory?.values.get(folderId) || false;
    }

    /**
     * @returns {number | string | false}
     */
    getSelectedFolderId() {
        return this.folderCategory?.activeValueId ?? false;
    }

    /**
     * @returns {Object | false}
     */
    getSelectedFolder() {
        return this.getFolderById(this.getSelectedFolderId());
    }

    /**
     * @returns {Object[]}
     */
    getFolderAndParents(folder) {
        const folders = [];
        while (folder) {
            folders.push(folder);
            folder = this.getFolderById(folder.folder_id || folder.user_folder_id);
        }
        return folders;
    }

    /**
     * @returns {Object[]}
     */
    getSelectedFolderAndParents() {
        return this.getFolderAndParents(
            this.getFolderById(this.getSelectedFolderId() || false),
        );
    }

    /**
     * @override
     */
    toggleCategoryValue(sectionId, valueId) {
        super.toggleCategoryValue(...arguments);

        const selectedFolder = this.getSelectedFolder();
        if (!this.context.documents_view_secondary) {
            browser.localStorage.setItem("searchpanel_documents_document", valueId);
            this.documentService.updateDocumentURL(selectedFolder);
        }
        if (typeof valueId === "number") {
            if (selectedFolder.childrenIds && selectedFolder.childrenIds.length) {
                this.documentService.logAccess(selectedFolder.access_token);
            } else {
                this.documentService
                    .logAccess(selectedFolder.access_token)
                    .then((result) => {
                        if (result && result?.reload) {
                            this._reloadSearchModel(true);
                        }
                    });
            }
        }
    }

    async _reloadSearchModel(reloadCategories) {
        if (reloadCategories) {
            await this._reloadSearchPanel(true);
        }
        await this._notify();
    }

    async _reloadSearchPanel(skipUpdate = false) {
        await this._fetchSections(
            this.getSections((s) => s.type === "category"),
            [],
        );
        if (!skipUpdate) {
            this.trigger("update-search-panel");
        }
    }

    /**
     * @override
     */
    _getCategoryDomain() {
        const userFolderCategory = this.folderCategory;
        if (["COMPANY", "MY", "RECENT"].includes(userFolderCategory.activeValueId)) {
            return [["user_folder_id", "=", userFolderCategory.activeValueId]];
        }
        if (userFolderCategory.activeValueId === "TRASH") {
            return [["active", "=", false]];
        }
        if (userFolderCategory.activeValueId === "SHARED") {
            return Domain.and([
                [["shortcut_document_id", "=", false]],
                [["user_folder_id", "=", "SHARED"]],
            ]).toList();
        }
        if (!userFolderCategory.activeValueId) {
            if (this.context.documents_unique_folder_id) {
                return [["id", "child_of", this.context.documents_unique_folder_id]];
            }
            return [];
        }
        const folder = this.getSelectedFolder();
        const folderIdToOpen = folder?.shortcut_document_id?.length
            ? folder.shortcut_document_id[0]
            : userFolderCategory.activeValueId;
        const result = super._getCategoryDomain();
        const folderLeafIdx = result.findIndex(
            (leaf) => leaf[0] === "user_folder_id" && leaf[1] === "=",
        );
        if (folderLeafIdx !== -1) {
            result.splice(folderLeafIdx, 1, ...[["folder_id", "=", folderIdToOpen]]);
        }
        return result;
    }

    /**
     * @override Force
     */
    get orderBy() {
        const activeFolderId = this.folderCategory?.activeValueId;
        if (activeFolderId === "TRASH") {
            return [
                { name: "create_date", asc: false },
                { name: "is_folder", asc: true },
            ];
        }
        if (activeFolderId === "RECENT") {
            return [
                { name: "is_folder", asc: false },
                { name: "last_access_date_group", asc: false },
                { name: "write_date", asc: false },
            ];
        }
        const orderBy = super.orderBy;
        if (!orderBy.length) {
            return [{ name: "create_date", asc: false }];
        }
        return orderBy;
    }

    get groupBy() {
        const groupBy = super.groupBy;
        if (!groupBy?.length && this.folderCategory?.activeValueId === "RECENT") {
            return ["last_access_date_group"];
        }
        return groupBy;
    }

    /**
     * @param {Object} category
     * @param {number|string|false} valueId
     * @returns {boolean}
     */
    _isCategoryValueReachable(category, valueId) {
        const queue = [...category.rootIds];
        const seen = new Set();
        while (queue.length) {
            const folderId = queue.pop();
            if (seen.has(folderId)) {
                continue;
            }
            seen.add(folderId);
            const folder = category.values.get(folderId);
            if (!folder) {
                continue;
            }
            if (folder.id === valueId) {
                return true;
            }
            queue.push(...folder.childrenIds);
        }
        return false;
    }

    /**
     * @override
     */
    _updateCategoryValue(category, valueIds) {
        if (
            valueIds.includes(category.activeValueId) &&
            this._isCategoryValueReachable(category, category.activeValueId)
        ) {
            return;
        }
        if (this.context.documents_init_folder_id !== undefined) {
            category.activeValueId = this.context.documents_init_folder_id || false;
            return;
        }
        const storageItem = browser.localStorage.getItem(
            "searchpanel_documents_document",
        );
        if (
            storageItem &&
            !["COMPANY", "MY", "RECENT", "SHARED", "TRASH"].includes(storageItem)
        ) {
            try {
                category.activeValueId = JSON.parse(storageItem);
            } catch {
                category.activeValueId = false;
            }
        } else {
            category.activeValueId = storageItem;
        }
        if (
            ["COMPANY", "MY", "RECENT", "SHARED", "TRASH"].includes(
                category.activeValueId,
            ) ||
            (valueIds.includes(category.activeValueId) &&
                this._isCategoryValueReachable(category, category.activeValueId))
        ) {
            return;
        }
        if (category.values.has(category.activeValueId)) {
            let newSection = category.values.get(
                category.values.get(category.activeValueId).parentId,
            );
            while (
                newSection &&
                !this._isCategoryValueReachable(category, newSection.id)
            ) {
                newSection = category.values.get(newSection.parentId);
            }
            if (newSection) {
                category.activeValueId =
                    newSection.id || valueIds[Number(valueIds.length > 1)];
            } else {
                category.activeValueId = this.documentService.userIsInternal
                    ? "COMPANY"
                    : valueIds[0];
            }
            browser.localStorage.setItem(
                "searchpanel_documents_document",
                category.activeValueId,
            );
        } else {
            category.activeValueId = false;
        }
    }

    /**
     * @override
     */
    _shouldWaitForData() {
        return true;
    }

    _updateRouteState(state) {
        router.pushState(state);
    }
}
