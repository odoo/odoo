/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { browser } from "@web/core/browser/browser";
import { SearchPanel } from "@web/search/search_panel/search_panel";
import { useNestedSortable } from "@web/core/utils/nested_sortable";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { utils as uiUtils } from "@web/core/ui/ui_service";
import { Component, onWillStart, useState } from "@odoo/owl";
import { toggleArchive } from "@documents/views/hooks";

const VALUE_SELECTOR = [".o_search_panel_category_value", ".o_search_panel_filter_value"].join();
const FOLDER_VALUE_SELECTOR = ".o_search_panel_category_value";
const LONG_TOUCH_THRESHOLD = 400;

/**
 * This file defines the DocumentsSearchPanel component, an extension of the
 * SearchPanel to be used in the documents kanban/list views.
 */

export class DocumentsSearchPanelItemSettingsPopover extends Component {
    static props = [
        "close", // Function, close the popover
        "createChildEnabled", // Whether we have the option to create a new child or not
        "onCreateChild", // Function, create new child
        "onEdit", // Function, edit element
    ];
}
DocumentsSearchPanelItemSettingsPopover.template =
    "documents.DocumentsSearchPanelItemSettingsPopover";

export class DocumentsSearchPanel extends SearchPanel {
    setup() {
        super.setup(...arguments);
        const { uploads } = useService("file_upload");
        this.documentUploads = uploads;
        useState(uploads);
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.user = useService("user");
        this.action = useService("action");
        this.popover = usePopover(DocumentsSearchPanelItemSettingsPopover, {
            onClose: () => this.onPopoverClose?.(),
            popoverClass: "o_search_panel_item_settings_popover",
        });
        this.dialog = useService("dialog");

        onWillStart(async () => {
            this.isDocumentManager = await this.user.hasGroup("documents.group_documents_manager");
        });

        useNestedSortable({
            ref: this.root,
            groups: ".o_search_panel_category",
            elements: "li:not(.o_all_or_trash_category)",
            enable: () => this.isDocumentManager,
            nest: true,
            nestInterval: 10,
            /**
             * When the placeholder moves, unfold the new parent and show/hide carets
             * where needed.
             * @param {DOMElement} parent - parent element of where the element was moved
             * @param {DOMElement} newGroup - group in which the element was moved
             * @param {DOMElement} prevPos.parent - element's parent before the move
             * @param {DOMElement} placeholder - hint element showing the current position
             */
            onMove: ({ parent, newGroup, prevPos, placeholder }) => {
                if (parent) {
                    parent.classList.add("o_has_treeEntry");
                    placeholder.classList.add("o_treeEntry");
                    const parentSectionId = parseInt(newGroup.dataset.sectionId);
                    const parentValueId = parseInt(parent.dataset.valueId);
                    this.state.expanded[parentSectionId][parentValueId] = true;
                } else {
                    placeholder.classList.remove("o_treeEntry");
                }
                if (prevPos.parent && !prevPos.parent.querySelector("li")) {
                    prevPos.parent.classList.remove("o_has_treeEntry");
                }
            },
            onDrop: async ({ element, parent, next }) => {
                const draggingFolderId = parseInt(element.dataset.valueId);
                const parentFolderId = parent ? parseInt(parent.dataset.valueId) : false;
                const beforeFolderId = next ? parseInt(next.dataset.valueId) : false;
                await this.orm.call("documents.folder", "move_folder_to", [
                    [draggingFolderId],
                    parentFolderId,
                    beforeFolderId,
                ]);
                await this._reloadSearchModel(true);
            },
        });
    }

    /**
     * Returns the fields that are supported for creating new subsections on the fly
     */
    get supportedEditionFields() {
        if (!this.isDocumentManager) {
            return [];
        }
        return ["folder_id", "tag_ids"];
    }

    get supportedNewChildModels() {
        if (!this.isDocumentManager) {
            return [];
        }
        return ["documents.folder", "documents.facet"];
    }

    get supportedDocumentsDropFields() {
        return ["folder_id", "tag_ids"];
    }

    isUploadingInFolder(folderId) {
        return Object.values(this.documentUploads).find(
            (upload) => upload.data.get("folder_id") === folderId
        );
    }

    //---------------------------------------------------------------------
    // Edition
    //---------------------------------------------------------------------

    getResModelResIdFromValueGroup(section, value, group) {
        if (value) {
            return [
                this.env.model.root.fields[section.fieldName].relation,
                section.values.get(value).id,
            ];
        } else if (group) {
            const resId = section.groups.get(group).id;
            if (section.groupBy === "facet_id") {
                return ["documents.facet", resId];
            }
        }
    }

    async _reloadSearchModel(reloadCategories) {
        const searchModel = this.env.searchModel;
        // By default the category is not reloaded.
        if (reloadCategories) {
            await searchModel._fetchSections(
                searchModel.getSections(
                    (s) => s.type === "category" && s.fieldName === "folder_id"
                ),
                []
            );
        }
        await searchModel._notify();
    }

    // Support for edition on mobile
    resetLongTouchTimer() {
        if (this.longTouchTimer) {
            browser.clearTimeout(this.longTouchTimer);
            this.longTouchTimer = null;
        }
    }

    onSectionValueTouchStart(ev, section, value, group) {
        if (!uiUtils.isSmall() || !this.supportedEditionFields.includes(section.fieldName)) {
            return;
        }
        this.touchStartMs = Date.now();
        if (!this.longTouchTimer) {
            this.longTouchTimer = browser.setTimeout(() => {
                this.openEditPopover(ev, section, value, group);
                this.resetLongTouchTimer();
            }, LONG_TOUCH_THRESHOLD);
        }
    }

    onSectionValueTouchEnd() {
        const elapsedTime = Date.now() - this.touchStartMs;
        if (elapsedTime < LONG_TOUCH_THRESHOLD) {
            this.resetLongTouchTimer();
        }
    }

    onSectionValueTouchMove() {
        this.resetLongTouchTimer();
    }

    async openEditPopover(ev, section, value, group) {
        const [resModel, resId] = this.getResModelResIdFromValueGroup(section, value, group);
        const target = ev.currentTarget || ev.target;
        const label = target.closest(".o_search_panel_label");
        const counter = label && label.querySelector(".o_search_panel_counter");
        this.popover.open(ev.target, {
            onEdit: () => {
                this.popover.close();
                this.state.showMobileSearch = false;
                this.editSectionValue(resModel, resId);
            },
            onCreateChild: () => {
                this.popover.close();
                this.addNewSectionValue(section, value || group);
            },
            createChildEnabled: this.supportedNewChildModels.includes(resModel),
        });
        target.classList.add("d-block");
        if (counter) {
            counter.classList.add("d-none");
        }
        this.onPopoverClose = () => {
            this.onPopoverClose = null;
            target.classList.remove("d-block");
            if (counter) {
                counter.classList.remove("d-none");
            }
        };
    }

    async addNewSectionValue(section, parentValue) {
        const resModel = section.fieldName === "folder_id" ? "documents.folder" : "documents.tag";
        const defaultName = resModel === "documents.folder" ? _t("New Workspace") : _t("New Tag");
        const createValues = {
            name: defaultName,
        };
        if (resModel === "documents.folder") {
            createValues.parent_folder_id = parentValue;
        } else if (resModel === "documents.tag") {
            createValues.facet_id = parentValue;
            // There is a unicity constraint on the name of the tag, so we need to make sure that the name is unique.
            const group = section.groups.get(parentValue);
            const groupValues = [...group.values.values()];
            let index = 2;
            while (groupValues.find((v) => v.display_name === createValues.name)) {
                createValues.name = defaultName + ` (${index++})`;
            }
        }
        await this.orm.create(resModel, [createValues], {
            context: {
                create_from_search_panel: true,
            },
        });
        await this._reloadSearchModel(resModel === "documents.folder" && !section.enableCounters);
        if (resModel === "documents.folder") {
            this.state.expanded[section.id][parentValue] = true;
        }
        this.render(true);
    }

    async editSectionValue(resModel, resId) {
        const formViewRef = resModel === "documents.folder" ? "documents.folder_view_form" : "";
        this.action.doAction(
            {
                res_model: resModel,
                res_id: resId,
                name: _t("Edit"),
                type: "ir.actions.act_window",
                target: "new",
                views: [[false, "form"]],
                context: {
                    create: false,
                    form_view_ref: formViewRef,
                },
            },
            {
                onClose: this._reloadSearchModel.bind(this, true),
            }
        );
        await this.env.model.env.documentsView.bus.trigger("documents-close-preview");
    }

    //---------------------------------------------------------------------
    // Data Transfer
    //---------------------------------------------------------------------

    /**
     * Gives the "dragover" class to the given element or remove it if none
     * is provided.
     * @private
     * @param {HTMLElement} [newDragFocus]
     */
    updateDragOverClass(newDragFocus) {
        const allSelected = this.root.el.querySelectorAll(":scope .o_drag_over_selector");
        for (const selected of allSelected) {
            selected.classList.remove("o_drag_over_selector");
        }
        if (newDragFocus) {
            newDragFocus.classList.add("o_drag_over_selector");
        }
    }

    isValidDragTransfer(section, value, target, dataTransfer) {
        if (dataTransfer.types.includes("o_documents_data")) {
            return (
                value.id &&
                target &&
                target.closest(VALUE_SELECTOR) &&
                this.supportedDocumentsDropFields.includes(section.fieldName)
            );
        } else if (dataTransfer.types.includes("o_documents_drag_folder")) {
            return (
                section.fieldName === "folder_id" &&
                this.draggingFolder.id !== value.id &&
                this.draggingFolder.parent_folder_id !== value.id &&
                target &&
                target.closest(FOLDER_VALUE_SELECTOR)
            );
        }
        return false;
    }

    /**
     * @param {Object} section
     * @param {Object} value
     * @param {DragEvent} ev
     */
    onDragEnter(section, value, ev) {
        if (!this.isValidDragTransfer(section, value, ev.currentTarget, ev.dataTransfer)) {
            this.updateDragOverClass(null);
            return;
        }
        this.updateDragOverClass(ev.currentTarget);
        if (value.childrenIds && value.childrenIds.length) {
            this.state.expanded[section.id][value.id] = true;
        }
    }

    onDragLeave(section, { relatedTarget, dataTransfer }) {
        if (!this.isValidDragTransfer(section, { id: -1 }, relatedTarget, dataTransfer)) {
            this.updateDragOverClass(null);
        }
    }

    async onDrop(section, value, ev) {
        this.updateDragOverClass(null);
        if (this.isValidDragTransfer(section, value, ev.relatedTarget, ev.dataTransfer)) {
            return;
        }
        if (ev.dataTransfer.types.includes("o_documents_data")) {
            await this.onDropDocuments(section, value, ev);
        }
    }

    /**
     * Allows the selected kanban cards to be dropped in folders (workspaces) or tags.
     * @private
     * @param {Object} section
     * @param {Object} value
     * @param {DragEvent} ev
     */
    async onDropDocuments(section, value, { currentTarget, dataTransfer }) {
        if (
            currentTarget.querySelector(".active") || // prevents dropping in the current folder
            !this.isValidDragTransfer(section, value, currentTarget, dataTransfer)
        ) {
            return;
        }
        const data = JSON.parse(dataTransfer.getData("o_documents_data"));
        if (section.fieldName === "folder_id") {
            const currentFolder = this.env.searchModel.getSelectedFolder();
            if ((currentFolder.id && !currentFolder.has_write_access) || !value.has_write_access) {
                return this.notification.add(
                    _t("You don't have the rights to move documents to that workspace"),
                    {
                        title: _t("Access Error"),
                        type: "warning",
                    }
                );
            }
            if (currentFolder.id === "TRASH") {
                const model = this.env.model;
                await this.orm.write("documents.document", data.recordIds, { folder_id: value.id });
                await toggleArchive(model, model.root.resModel, data.recordIds, false);
                return;
            }
            // Dropping in the trash
            if (value.id === "TRASH") {
                const model = this.env.model;
                const callback = async () => {
                    await toggleArchive(model, model.root.resModel, data.recordIds, true);
                };
                model.root.records[0].openDeleteConfirmationDialog(model.root, callback, false);
                return;
            }
        }
        if (data.lockedCount) {
            return this.notification.add(
                _t(
                    "%s file(s) not moved because they are locked by another user",
                    data.lockedCount
                ),
                { title: _t("Partial transfer"), type: "warning" }
            );
        }
        if (section.fieldName === "folder_id") {
            this.env.searchModel.updateRecordFolderId(data.recordIds, value.id);
        } else {
            this.env.searchModel.updateRecordTagId(data.recordIds, value.id);
        }
    }

    /**
     * Handles the resize feature on the sidebar
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onStartResize(ev) {
        // Only triggered by left mouse button
        if (ev.button !== 0) {
            return;
        }

        const initialX = ev.pageX;
        const initialWidth = this.root.el.offsetWidth;
        const resizeStoppingEvents = ["keydown", "mousedown", "mouseup"];

        // Mousemove event : resize header
        const resizePanel = (ev) => {
            ev.preventDefault();
            ev.stopPropagation();
            const delta = ev.pageX - initialX;
            const newWidth = Math.max(10, initialWidth + delta);
            this.root.el.style["min-width"] = `${newWidth}px`;
        };
        document.addEventListener("mousemove", resizePanel, true);

        // Mouse or keyboard events : stop resize
        const stopResize = (ev) => {
            // Ignores the initial 'left mouse button down' event in order
            // to not instantly remove the listener
            if (ev.type === "mousedown" && ev.button === 0) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();

            document.removeEventListener("mousemove", resizePanel, true);
            resizeStoppingEvents.forEach((stoppingEvent) => {
                document.removeEventListener(stoppingEvent, stopResize, true);
            });
            // we remove the focus to make sure that the there is no focus inside
            // the panel. If that is the case, there is some css to darken the whole
            // thead, and it looks quite weird with the small css hover effect.
            document.activeElement.blur();
        };
        // We have to listen to several events to properly stop the resizing function. Those are:
        // - mousedown (e.g. pressing right click)
        // - mouseup : logical flow of the resizing feature (drag & drop)
        // - keydown : (e.g. pressing 'Alt' + 'Tab' or 'Windows' key)
        resizeStoppingEvents.forEach((stoppingEvent) => {
            document.addEventListener(stoppingEvent, stopResize, true);
        });
    }
}

DocumentsSearchPanel.modelExtension = "DocumentsSearchPanel";

if (!uiUtils.isSmall()) {
    DocumentsSearchPanel.template = "documents.SearchPanel";
    DocumentsSearchPanel.subTemplates = {
        category: "documents.SearchPanel.Category",
        filtersGroup: "documents.SearchPanel.FiltersGroup",
    };
} else {
    DocumentsSearchPanel.subTemplates = {
        category: "documents.SearchPanel.Category.Small",
        filtersGroup: "documents.SearchPanel.FiltersGroup.Small",
    };
}
