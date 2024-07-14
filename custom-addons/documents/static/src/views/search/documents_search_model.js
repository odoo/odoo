/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { SearchModel } from "@web/search/search_model";
import { browser } from "@web/core/browser/browser";
import { parseHash } from "@web/core/browser/router_service";
import { useSetupAction } from "@web/webclient/actions/action_hook";

import { onWillStart } from "@odoo/owl";

// Helpers
const isFolderCategory = (s) => s.type === "category" && s.fieldName === "folder_id";
const isTagFilter = (s) => s.type === "filter" && s.fieldName === "tag_ids";

export class DocumentsSearchModel extends SearchModel {

    setup(services) {
        super.setup(services);
        onWillStart(async () => {
            this.deletionDelay = await this.orm.call("documents.document", "get_deletion_delay", [[]]);
        });
        useSetupAction({
            beforeLeave: () => {
                this._updateRouteState({ folder_id: undefined, tag_ids: undefined }, false);
            },
        });
    }

    async load(config) {
        await super.load(...arguments);

        const urlHash = parseHash(browser.location.hash);
        const folderId = urlHash.folder_id || this.getSelectedFolderId();
        const tagIds = urlHash.tag_ids;

        if (folderId) {
            const folderSection = this.getSections(isFolderCategory)[0];
            if (folderSection) {
                this.toggleCategoryValue(folderSection.id, folderId);
            }
        }
        if (tagIds) {
            const tagSection = this.getSections(isTagFilter)[0];
            if (tagSection) {
                this.toggleFilterValues(tagSection.id, String(tagIds).split(",").map(Number));
            }
        }
    }

    //---------------------------------------------------------------------
    // Actions / Getters
    //---------------------------------------------------------------------

    /**
     * Returns a description of each folder (record of documents.folder).
     * @returns {Object[]}
     */
    getFolders() {
        const { values } = this.getSections(isFolderCategory)[0];
        return [...values.values()];
    }

    /**
     * Returns the id of the current selected folder, if any, false
     * otherwise.
     * @returns {number | false}
     */
    getSelectedFolderId() {
        const { activeValueId } = this.getSections(isFolderCategory)[0];
        return activeValueId;
    }

    /**
     * Returns the current selected folder, if any, false otherwise.
     * @returns {Object | false}
     */
    getSelectedFolder() {
        const folderSection = this.getSections(isFolderCategory)[0];
        const folder = folderSection && folderSection.values.get(folderSection.activeValueId);
        return folder || false;
    }

    /**
     * Returns ids of selected tags.
     * @returns {number[]}
     */
    getSelectedTagIds() {
        const { values } = this.getSections(isTagFilter)[0];
        return [...values.values()].filter((value) => value.checked).map((value) => value.id);
    }

    /**
     * Returns a description of each tag (record of documents.tag).
     * @returns {Object[]}
     */
    getTags() {
        const { values } = this.getSections(isTagFilter)[0];
        return [...values.values()].sort((a, b) => {
            if (a.group_sequence === b.group_sequence) {
                return a.sequence - b.sequence;
            } else {
                return a.group_sequence - b.group_sequence;
            }
        });
    }

    /**
     * Overridden to write the new value in the local storage.
     * And to write the folder_id in the url.
     * @override
     */
    toggleCategoryValue(sectionId, valueId) {
        super.toggleCategoryValue(...arguments);
        const { fieldName } = this.sections.get(sectionId);
        const storageKey = this._getStorageKey(fieldName);
        browser.localStorage.setItem(storageKey, valueId);

        if (fieldName === "folder_id") {
            this._updateRouteState({ folder_id: valueId, tag_ids: undefined }, true);
        }
    }

    /**
     * Overriden to write the tag_ids in the url.
     * @override
     */
    toggleFilterValues(sectionId, valueIds, forceTo = null) {
        super.toggleFilterValues(...arguments);
        const { fieldName } = this.sections.get(sectionId);
        if (fieldName === "tag_ids") {
            this._updateRouteState({ tag_ids: this.getSelectedTagIds() }, true);
        }
    }

    /**
     * Updates the folder id of a record matching the given value.
     * @param {number[]} recordIds
     * @param {number} valueId
     */
    async updateRecordFolderId(recordIds, valueId) {
        await this.orm.write("documents.document", recordIds, {
            folder_id: valueId,
        });
        this.trigger("update");
    }

    /**
     * Updates the tag ids of a record matching the given value.
     * @param {number[]} recordIds
     * @param {number} valueId
     * @param {number} x2mCommand command (4 to add a tag, 3 to remove it)
     */
    async updateRecordTagId(recordIds, valueId, x2mCommand = 4) {
        await this.orm.write("documents.document", recordIds, {
            tag_ids: [[x2mCommand, valueId]],
        });
        this.trigger("update");
        await this.reload();  // update the tag count
    }

    //---------------------------------------------------------------------
    // Private
    //---------------------------------------------------------------------

    /**
     * Adds a new fake folder to see all currently archived documents.
     * @override
     */
    async _fetchCategories() {
        const result = await super._fetchCategories(...arguments);
        const folderCategory = this.categories.find((cat) => cat.fieldName === "folder_id");
        if (!folderCategory) {
            return result;
        }
        if (!folderCategory.rootIds.includes("TRASH")) {
            folderCategory.rootIds.push("TRASH");
        }
        if (!folderCategory.values.has("TRASH")) {
            folderCategory.values.set("TRASH", {
                bold: true,
                childrenIds: [],
                display_name: _t("Trash"),
                id: "TRASH",
                parentId: false,
                has_write_access: true,
                description: _t(
                    "Items in trash will be deleted forever after %s days.", this.deletionDelay
                ),
            });
        }
        return result;
    }

    /**
     * Make sure we use the correct domain instead of folder_id = 0.
     * @override
     */
    _getCategoryDomain() {
        const folderCategory = this.categories.find((cat) => cat.fieldName === "folder_id");
        if (folderCategory.activeValueId === "TRASH") {
            return [["active", "=", false]];
        }
        const result = super._getCategoryDomain();
        const folderLeafIdx = result.findIndex(
            (leaf) => leaf[0] === "folder_id" && leaf[1] === "child_of"
        );
        if (folderLeafIdx !== -1) {
            result.splice(
                folderLeafIdx,
                1,
                ...[["folder_id", "child_of", folderCategory.activeValueId]]
            );
        }
        return result;
    }

    _isCategoryValueReachable(category, valueId) {
        const queue = [...category.rootIds];
        let folder;
        while ((folder = category.values.get(queue.pop()))) {
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
    _ensureCategoryValue(category, valueIds) {
        if (valueIds.includes(category.activeValueId) && this._isCategoryValueReachable(category, category.activeValueId)) {
            return;
        }
        // If not set in context, or set to an unknown value, set active value
        // from localStorage
        const storageKey = this._getStorageKey(category.fieldName);
        const storageItem = browser.localStorage.getItem(storageKey);
        category.activeValueId =
            storageItem && storageItem !== "TRASH" ? JSON.parse(storageItem) : storageItem;
        if (
            category.activeValueId === "TRASH" ||
            (valueIds.includes(category.activeValueId) &&
                this._isCategoryValueReachable(category, category.activeValueId))
        ) {
            return;
        }
        // valueIds might contain different values than category.values
        if (category.values.has(category.activeValueId)) {
            // We might be in a deleted subfolder, try to find the parent.
            let newSection = category.values.get(category.values.get(category.activeValueId).parentId);
            while (!this._isCategoryValueReachable(category, newSection.id)) {
                newSection = category.values.get(newSection.parentId);
            }
            category.activeValueId = newSection.id || valueIds[Number(valueIds.length > 1)];
            browser.localStorage.setItem(storageKey, category.activeValueId);
        } else {
            // If still not a valid value, get the search panel default value
            // from the given valid values.
            category.activeValueId = valueIds[Number(valueIds.length > 1)];
        }
    }

    /**
     * @private
     * @param {string} fieldName
     * @returns {string}
     */
    _getStorageKey(fieldName) {
        return `searchpanel_${this.resModel}_${fieldName}`;
    }

    /**
     * @override
     */
    _shouldWaitForData() {
        return true;
    }

    _updateRouteState(state, lock) {
        this.env.services.router.pushState(state, { lock: lock });
    }

}
