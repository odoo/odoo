/** @odoo-module **/

import { PdfGroupName } from "@documents/owl/components/pdf_group_name/pdf_group_name";
import { PdfPage } from "@documents/owl/components/pdf_page/pdf_page";
import { loadPDFJSAssets } from "@web/libs/pdfjs";
import { useCommand } from "@web/core/commands/command_hook";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";
import { useActiveElement } from "@web/core/ui/ui_service";
import { uniqueId } from "@web/core/utils/functions";
import { useService } from "@web/core/utils/hooks";

import { ExitSplitToolsDialog } from "@documents/owl/components/pdf_exit_dialog/pdf_exit_dialog";

import { Component, onWillStart, toRaw, useRef, useState, useEffect } from "@odoo/owl";

const BLANK_PAGE_THRESHOLD = 2500;
const BLANK_PIXEL_FILTER_VALUE = 220;

export class PdfManager extends Component {
    static components = {
        Dialog,
        PdfPage,
        PdfGroupName,
    };
    static defaultProps = {
        embeddedActions: [],
    };
    static props = {
        documents: Array,
        embeddedActions: { type: Array, optional: true },
        onProcessDocuments: { type: Function },
        close: { type: Function },
    };
    static template = "documents.component.PdfManager";

    setup() {
        this.root = useRef("root");
        //setting the active element allows restricting the command palette to the context of this Component
        //this is necessary because this Component is a modal in disguise but does not properly override "Dialog"
        useActiveElement("root");
        this.pageViewer = useRef("pageViewer");
        this.selectionBox = useRef("selectionBox");
        this.addFileInput = useRef("addFileInput");
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.commandService = useService("command");
        this.state = useState({
            // Disables upload button if currently uploading.
            uploadingLock: false,
            /*
             * Will be sent to the backend.
             * object groupData[groupId] = { groupId, name, pageIds }
             */
            groupData: {},
            // Ordered list of groups (should be set)
            groupIds: [],
            /*
             * Will be sent to the backend.
             *  object pages[pageId] = { pageId, groupId, fileId, localPageNumber, isSelected}
             */
            pages: {},
            // object pageCanvases[pageId] = { canvas, pageObject }
            pageCanvases: {},
            // The page that has the focus
            focusedPage: undefined,
            // The last selected page
            lastSelectedPage: undefined,
            // The page that is open as large preview.
            viewedPage: undefined,
            // The page's name that is open as large preview.
            viewedPageName: undefined,
            // The page's index that is open as large preview.
            viewedPageIndex: undefined,
            // Number of pages in the split tools.
            numberOfPages: undefined,
            // whether to archive the original documents.
            archive: true,
            // Whether to keep the document(s) or not.
            keepDocument: true,
            // Whether there are remaining pages to process.
            remaining: false,
            //name of the opened document
            fileName: "",
            // edit on group name
            edit: false,
            isSelecting: false,
            selectionBoxArgs: { left: "0px", top: "0px", width: "0px", height: "0px" },
        });

        this._exitSplitToolsClick = false;
        this._newFiles = {};
        this._selectionX = 0.0;
        this._selectionY = 0.0;
        this._selectionScrollTop = 0.0;
        this._selectionScrollLeft = 0.0;
        this._embeddedActionApplied = false;
        this._onMouseDown = this._onMouseDown.bind(this);
        this._onMouseUp = this._onMouseUp.bind(this);
        this._onMouseMove = this._onMouseMove.bind(this);
        this._onShiftDown = this._onShiftDown.bind(this);
        this._setUseCommand = this._setUseCommand.bind(this);
        this._exitSplitTools = this._exitSplitTools.bind(this);

        onWillStart(async () => {
            await this._loadAssets();
        });

        useEffect(
            () => {
                const _onOutsideClick = this._onOutsideClick.bind(this);
                if (this.props.documents.length === 1) {
                    this.state.fileName = this._removePdfExtension(this.props.documents[0].name);
                }
                for (const pdf_document of this.props.documents) {
                    this._addFile(pdf_document.name, {
                        url: `/documents/content/${encodeURIComponent(pdf_document.access_token)}`,
                        documentId: pdf_document.id,
                    });
                }
                document.addEventListener("click", _onOutsideClick, true);
                document.addEventListener("mousedown", this._onMouseDown, true);
                document.addEventListener("mouseup", this._onMouseUp, true);
                document.addEventListener("mousemove", this._onMouseMove, true);
                document.addEventListener("keydown", this._onShiftDown, true);
                return () => {
                    document.removeEventListener("click", _onOutsideClick, true);
                    document.removeEventListener("mousedown", this._onMouseDown, true);
                    document.removeEventListener("mouseup", this._onMouseUp, true);
                    document.removeEventListener("mousemove", this._onMouseMove, true);
                    document.removeEventListener("keydown", this._onShiftDown, true);
                };
            },
            () => []
        );

        // Shortcuts and navigation
        this._setUseCommand(
            _t("Focus previous page"),
            this._focusNextPage.bind(this, "left", false),
            "arrowleft",
            {
                allowRepeat: true,
            }
        );
        this._setUseCommand(
            _t("Focus next page"),
            this._focusNextPage.bind(this, "right", false),
            "arrowright",
            {
                allowRepeat: true,
            }
        );
        this._setUseCommand(
            _t("Focus first page of previous group"),
            this._focusNextGroup.bind(this, "left"),
            "control+ArrowLeft"
        );
        this._setUseCommand(
            _t("Focus first page of next group"),
            this._focusNextGroup.bind(this, "right"),
            "control+ArrowRight"
        );
        this._setUseCommand(_t("Select focused page"), this._spaceKeySelect.bind(this), "control+space", {
            allowRepeat: true,
        });
        this._setUseCommand(
            _t("Select/Deselect all pages"),
            this._selectAll.bind(this),
            "control+a"
        );
        this._setUseCommand(
            _t("Select previous page"),
            this._focusNextPage.bind(this, "left", true),
            "shift+ArrowLeft",
            {
                allowRepeat: true,
            }
        );
        this._setUseCommand(
            _t("Select next page"),
            this._focusNextPage.bind(this, "right", true),
            "shift+ArrowRight",
            {
                allowRepeat: true,
            }
        );
        this._setUseCommand(
            _t("Select previous pages of the group"),
            this._selectUntilSplit.bind(this, "left"),
            "control+shift+ArrowLeft"
        );
        this._setUseCommand(
            _t("Select next pages of the group"),
            this._selectUntilSplit.bind(this, "right"),
            "control+shift+ArrowRight"
        );
        this._setUseCommand(
            _t("Escape Preview/Deselect/Exit"),
            this._onPushExit.bind(this),
            "escape"
        );
        this._setUseCommand(
            _t("Split selected pages"),
            this._splitSelectionHandler.bind(this),
            "control+s",
            {
                allowRepeat: true,
            }
        );
        this._setUseCommand(
            _t("Split all white pages"),
            this._splitWhitePagesHandler.bind(this),
            "shift+s",
        );
        this._setUseCommand(
            _t("Delete focused or selected pages"),
            this.onArchive.bind(this),
            "alt+backspace"
        );
        useHotkey("ArrowDown", this._focusNextPage.bind(this, "down", false), {
            allowRepeat: true,
        });
        useHotkey("ArrowUp", this._focusNextPage.bind(this, "up", false), { allowRepeat: true });
        useHotkey("shift+ArrowDown", this._focusNextPage.bind(this, "down", true), {
            allowRepeat: true,
        });
        useHotkey("shift+ArrowUp", this._focusNextPage.bind(this, "up", true), {
            allowRepeat: true,
        });
        useHotkey("enter", this._togglePreviewer.bind(this), {
            allowRepeat: true,
        });
        useHotkey("delete", this.onArchive.bind(this));
    }

    /**
     * Set the useCommand hook for shortcuts
     * @param {String} name
     * @param {Function} callback
     * @param {String} hotkey
     * @param {Object} options
     * @private
     */
    _setUseCommand(name, callback, hotkey, options) {
        useCommand(name, callback, {
            category: "smart_action",
            hotkey: hotkey,
            hotkeyOptions: options,
        });
    }

    //--------------------------------------------------------------------------
    // Getters / Setters
    //--------------------------------------------------------------------------

    /**
     * @return {String[]}
     */
    get ignoredPageIds() {
        return Object.keys(this.state.pages).filter(
            (key) => !this.state.pages[key].isSelected && this.state.pages[key].groupId
        );
    }
    /**
     * @return {String[]}
     */
    get selectedPageIds() {
        return Object.keys(this.state.pages).filter(
            (key) => this.state.pages[key].isSelected && this.state.pages[key].groupId
        );
    }
    /**
     * @return {Boolean}
     */
    get isDebugMode() {
        return Boolean(odoo.debug);
    }
    /**
     * @return {String[]}
     */
    get allSelected() {
        return !Object.values(this.state.pages).some((page) => !page.isSelected);
    }
    /**
     * @return {String[]}
     */
    get sortedPagesIds() {
        return this.state.groupIds.flatMap((groupId) =>
            Object.values(this.state.groupData[groupId].pageIds)
        );
    }

    //----------------------------------------------------------------------
    // Handlers
    //----------------------------------------------------------------------

    /**
     * Toggle the edit of groups names when double clicking on the name
     * @public
     * @param {String} groupId
     * @param {Boolean} toggle
     */
    onToggleEdit(groupId, toggle) {
        this.state.edit = toggle ? groupId : false;
        const toggleActivation = this.state.groupData[groupId].pageIds.some(
            (pageId) => this.state.pages[pageId].isSelected !== true
        );
        this.state.groupData[groupId].pageIds.map((pageId) => {
            this.state.pages[pageId].isSelected = toggleActivation;
        });
        this.state.focusedPage = undefined;
    }
    /**
     * Returns the number of cards per line
     * @private
     */
    _computeCardsPerLine() {
        const allPages = [...document.querySelectorAll(".o_documents_pdf_page_frame")];
        const top = allPages[0].getBoundingClientRect().top;
        return allPages.filter((page) => page.getBoundingClientRect().top === top).length;
    }
    /**
     * Deselect every page
     * @private
     */
    _unSelectPages() {
        for (const pageId of this.selectedPageIds) {
            this.state.pages[pageId].isSelected = false;
        }
    }
    /**
     * Handles the activation/desactivation of the splitters in the active pages
     * @private
     */
    _splitSelectionHandler() {
        if (this.state.viewedPage) {
            return;
        }
        const selectedPages = this.selectedPageIds;
        const focusedPageisSelected = selectedPages.includes(this.state.focusedPage);
        const sortedPagesIds = this.sortedPagesIds;
        if (this.state.focusedPage && !focusedPageisSelected) {
            const indexPage = sortedPagesIds.indexOf(this.state.focusedPage);
            const previousPageId = sortedPagesIds[indexPage - 1];
            if (indexPage !== 0) {
                this._pageSeparator(previousPageId, this.state.pages[previousPageId].groupId);
            }
            return;
        }
        let toggleSeparatorBool = true;
        const pagesToSplit = [];
        const pagesToGather = [];
        for (const pageId of selectedPages) {
            const indexPage = sortedPagesIds.indexOf(pageId);
            if (
                indexPage < sortedPagesIds.length - 1 &&
                this.state.pages[sortedPagesIds[indexPage + 1]].isSelected
            ) {
                const parent = document
                    .querySelector(`[data-id=${pageId}]`)
                    .closest(".o_documents_pdf_page_frame");
                const isSeparatorActive = parent.nextElementSibling.classList.contains(
                    "o_pdf_separator_selected"
                );
                toggleSeparatorBool = toggleSeparatorBool && isSeparatorActive;
                if (isSeparatorActive) {
                    pagesToGather.push(this.state.pages[pageId]);
                } else {
                    pagesToSplit.push(this.state.pages[pageId]);
                }
            }
        }
        const pagesToTreat = toggleSeparatorBool ? pagesToGather : pagesToSplit;
        for (const page of pagesToTreat) {
            this._pageSeparator(page.pageId, page.groupId);
        }
    }
    /**
     * Handles the split of all the whites pages in the document.
     * This method will traverse all the pages sequentially and create groups
     * delimited by a (or some) white page(s). It will ease the user experience
     * when processing scanned documents.
     */
    async _splitWhitePagesHandler() {
        let precedingPageIsBlank = false;
        let docCount = 1;
        const allPagesIds = this.sortedPagesIds;
        this.state.groupData = {};
        this.state.groupIds = [];
        this._createGroup({
            pageIds: allPagesIds,
            name: this.state.pages[allPagesIds[0]].isBlank
                ? _t("Blank Page")
                : _t("sub-doc-%s", docCount++),
        });
        for (const pageId in this.state.pages) {
            const page = this.state.pages[pageId];
            const createGroup = (name) => {
                const group = this.state.groupData[page.groupId];
                const groupPageIds = group.pageIds;
                const newGroupPageIds = groupPageIds.slice(groupPageIds.indexOf(pageId));
                this._createGroup({
                    name: name,
                    pageIds: newGroupPageIds,
                });
                group.pageIds = groupPageIds.filter((page) => !newGroupPageIds.includes(page));
            };
            if (page.isBlank && !precedingPageIsBlank) {
                createGroup(_t("Blank Page"));
            } else if (!page.isBlank && precedingPageIsBlank) {
                createGroup(_t("sub-doc-%s", docCount++));
            }
            page.isSelected = !page.isBlank;
            precedingPageIsBlank = page.isBlank;
        }
    }
    /**
     * Puts a splitter between 2 adjacent pages and modify the groups accordingly
     * @private
     * @param {String} pageId
     * @param {String} groupId
     */
    _pageSeparator(pageId, groupId) {
        const page = this.state.pages[pageId];
        const groupPageIds = this.state.groupData[groupId].pageIds;
        const pageIndex = groupPageIds.indexOf(pageId);
        const groupIndex = this.state.groupIds.indexOf(groupId);
        const isLastPage = pageIndex === groupPageIds.length - 1;

        if (isLastPage) {
            // merging the following group into the current one.
            const targetGroupId = this.state.groupIds[groupIndex + 1];
            if (targetGroupId) {
                const pageIds = this.state.groupData[targetGroupId].pageIds;
                for (const pageId of pageIds) {
                    this._addPage(pageId, page.groupId);
                }
            }
        } else {
            // making a new group with all the following pages.
            const newGroupPages = groupPageIds.slice(pageIndex + 1);
            const newGroupId = this._createGroup({
                index: groupIndex + 1,
            });
            for (const page of newGroupPages) {
                this._addPage(page, newGroupId);
            }
        }
    }
    /**
     * Add pdf file inside the split tools
     * @private
     * @param {String} name
     * @param {Object} param1
     * @param {number} [param1.documentId] the id of the `documents.document` record.
     * @param {Object} [param1.file]
     * @param {String} [param1.url]
     */
    async _addFile(name, { documentId, file, url }) {
        if (!url) {
            if (!file && !documentId) {
                return;
            }
            url = URL.createObjectURL(file);
        }
        this.state.uploadingLock = true;
        const fileId = uniqueId("file");
        const pdf = await this._getPdf(url);

        if (file) {
            this._newFiles[fileId] = { type: "file", file };
        } else if (documentId) {
            this._newFiles[fileId] = { type: "document", documentId };
        }
        name = this._removePdfExtension(name || _t("New File"));

        const pageCount = pdf.numPages;
        const { pageIds, newPages } = this._createPages({ fileId, name, pageCount });
        this._newFiles[fileId].pageIds = this._newFiles[fileId].selectedPageIds = pageIds;
        this.state.uploadingLock = false;

        await this._loadCanvases({ newPages, pageCount, pdf });
    }
    /**
     * Adds a page to a group (also removes the page from its
     * former group).
     * @private
     * @param {String} pageId
     * @param {String} groupId
     * @param {Object} param2
     * @param {String} [param2.index]
     */
    _addPage(pageId, groupId, { index } = {}) {
        if (!this.state.groupData[groupId]) {
            return;
        }
        this._removePage(pageId);
        if (index !== undefined) {
            this.state.groupData[groupId].pageIds.splice(index, 0, pageId);
        } else {
            this.state.groupData[groupId].pageIds.push(pageId);
        }
        this.state.pages[pageId].groupId = groupId;
        this.state.numberOfPages = this.sortedPagesIds.length;
    }
    /**
     * @private
     * @param {String} message
     */
    _displayErrorNotification(message) {
        this.notification.add(message, {
            title: _t("Error"),
        });
    }
    /**
     * @private
     * @param {number} number
     */
    _displayNumberCreatedDocuments(number) {
        this.notification.add(_t("%s new document(s) created", number), { type: "success" });
    }
    /**
     * @private
     * @param {number} number
     */
    _displayNumberDeletedPages(number) {
        this.notification.add(_t("%s page(s) deleted", number), { type: "success" });
    }
    /**
     * Ignored pages are not committed but are instead kept in the
     * PDF Manager. If no ignored page remain, the PDF Manager closes and the
     * view is reloaded.
     * @private
     * @param {number} [actionId]
     */
    async _applyChanges(actionId) {
        let processedPageIds = this.selectedPageIds;
        let pageIds = this.ignoredPageIds;
        if (processedPageIds.length === 0 && !this.state.focusedPage) {
            this._displayErrorNotification(_t("No document has been selected"));
            return;
        }
        if (processedPageIds.length === 0) {
            processedPageIds = [this.state.focusedPage];
            pageIds = pageIds.filter((pageId) => pageId !== this.state.focusedPage);
        }
        const exit = !pageIds.length;

        let fileName = _t("Remaining Pages");
        if (this.state.fileName) {
            fileName = this.state.fileName + " " + fileName;
        }
        try {
            const documentIds = await this._sendChanges();
            await this.props.onProcessDocuments({ documentIds, actionId, exit });
            this._displayNumberCreatedDocuments(documentIds.length);
            if (!exit) {
                this._embeddedActionApplied = true;
                for (const pageId of processedPageIds) {
                    this._removePage(pageId, { fromFile: true });
                }
            } else {
                this.props.close();
            }
        } catch (error) {
            this._displayErrorNotification(error.message || error);
            if (pageIds.length) {
                this._createGroup({ name: fileName, pageIds: pageIds, isSelected: true });
            }
        } finally {
            this.state.uploadingLock = false;
            this.state.remaining = true;
            this.state.numberOfPages = this.sortedPagesIds.length;
        }
    }
    /**
     * @private
     * @param {Object} [param0]
     * @param {String} [param0.name]
     * @param {number[]} [param0.pageIds]
     * @param {number} [param0.index]
     * @param {boolean} [param0.isSelected] true if pages should be selected
     * @return {String} groupId (unique)
     */
    _createGroup({ name, pageIds, index, isSelected } = {}) {
        const groupId = uniqueId("group");
        pageIds = pageIds || [];
        this.state.groupData[groupId] = {
            groupId,
            name: name || _t("New Group"),
            pageIds,
        };
        for (const pageId of pageIds) {
            this.state.pages[pageId].groupId = groupId;
            if (isSelected !== undefined) {
                this.state.pages[pageId].isSelected = isSelected;
            }
        }
        if (index) {
            this.state.groupIds.splice(index, 0, groupId);
        } else {
            this.state.groupIds.push(groupId);
        }
        return groupId;
    }

    /**
     * This method will check if the page contains any text (for computer
     * generated pdf) and for the image pixels if it's a scanned pdf.
     */
    async _isBlankPage(page, canvas) {
        const pageContent = await page.getTextContent();
        const hasText = pageContent.items.length > 0;
        return !hasText && this._hasBlankGraphics(canvas);
    }

    /**
     * This method will check the canvas for each pixel based on its color.
     * If the sum of all the color code for each pixel doesn't exceed the
     * empirically tested threshold the image is considered as blank.
     * It's used to detect scanned blank page (they are never really empty...)
     */
    async _hasBlankGraphics(canvas) {
        const pixels = canvas
            .getContext("2d")
            .getImageData(0, 0, canvas.width, canvas.height, { colorSpace: "display-p3" }).data;
        let totalSum = 0;
        for (const pixel of pixels) {
            if (pixel < BLANK_PIXEL_FILTER_VALUE) {
                totalSum += 255 - pixel;
                if (totalSum >= BLANK_PAGE_THRESHOLD) {
                    return false;
                }
            }
        }
        return true;
    }

    /**
     * @private
     * @param {Object} [param0]
     * @param {String} [param0.name]
     * @param {String} [param0.fileId]
     * @param {number} [param0.pageCount]
     * @return {Object} { pageIds, newPages }
     * @return {Array<String>} pageIds
     * @return {Object} newPages
     */
    _createPages({ fileId, name, pageCount }) {
        let groupId;
        let groupName = name;
        const multipleFiles = this.props.documents.length > 1;
        let groupLock = false;
        const pageIds = [];
        const newPages = {};
        // creating page and groups
        for (let pageNumber = 0; pageNumber < pageCount; pageNumber++) {
            // creating multiple groups if single file
            if (multipleFiles && !groupLock) {
                groupId = this._createGroup({ name: groupName });
                groupLock = true;
            } else if (!multipleFiles) {
                groupName = `${name}-p${pageNumber + 1}`;
                groupId = this._createGroup({ name: groupName });
            }
            const pageId = uniqueId("page");
            this.state.pages[pageId] = {
                pageId,
                groupId,
                fileId,
                localPageNumber: pageNumber + 1,
                isSelected: true,
            };
            newPages[pageNumber + 1] = pageId;
            this.state.pageCanvases[pageId] = {};
            this.state.groupData[groupId].pageIds.push(pageId);
            pageIds.push(pageId);
        }
        this.state.numberOfPages = this.sortedPagesIds.length;
        return { pageIds, newPages };
    }
    /**
     * To be overwritten in tests (along with _renderCanvas()).
     * @private
     * @param {String} url
     * @return {PdfJsObject} pdf
     *    should be constructed as follow:
     *        pdf.getPage(pageNumber) {function} return {pageObject}
     *        pdf.numPages {number}
     */
    async _getPdf(url) {
        return globalThis.pdfjsLib.getDocument(url).promise;
    }
    /**
     * To be overwritten in tests.
     * @private
     */
    async _loadAssets() {
        await loadPDFJSAssets();
    }
    /**
     * @private
     * @param {Object} [param0]
     * @param {Object} [param0.newPages]
     * @param {number} [param0.pageCount]
     * @param {PdfjsObject} [param0.pdf]
     */
    async _loadCanvases({ newPages, pageCount, pdf }) {
        for (let pageNumber = 1; pageNumber <= pageCount; pageNumber++) {
            if (!this.root.el) {
                break;
            }
            const pageId = newPages[pageNumber];
            const page = await pdf.getPage(pageNumber);
            const canvas = await this._renderCanvas(toRaw(page), {
                width: 160,
                height: 230,
            });
            this.state.pageCanvases[pageId] = { page, canvas };
            this.state.pages[pageId].isBlank = await this._isBlankPage(page, canvas);
        }
    }
    /**
     * @private
     * @param {Object} page
     * @param {Object} param1
     * @param {number} param1.width
     * @param {number} param1.height
     * @return {DomElement} canvas
     */
    async _renderCanvas(page, { width, height }) {
        const viewPort = page.getViewport({ scale: 1 });
        const isLandscape = viewPort.width > viewPort.height;
        const canvas = document.createElement("canvas");
        canvas.className = "o_documents_pdf_canvas";
        canvas.width = width;
        canvas.height = height;
        const scale = isLandscape
            ? Math.min(canvas.width / viewPort.height, canvas.height / viewPort.width)
            : Math.min(canvas.width / viewPort.width, canvas.height / viewPort.height);
        await page.render({
            canvasContext: canvas.getContext("2d"),
            viewport: page.getViewport({ scale, rotation: isLandscape ? 270 : viewPort.rotation }),
        }).promise;
        return canvas;
    }
    /**
     * Endpoint of the manager, sends the page structure to be split to the
     * server and closes the manager.
     * @private
     */
    async _sendChanges() {
        this.state.uploadingLock = true;
        const fileIds = [];
        const files = [];
        for (const key in this._newFiles) {
            if (this._newFiles[key].type === "file") {
                files.push(this._newFiles[key].file);
                fileIds.push(key);
            }
        }
        const fileGroups = Object.values(JSON.parse(JSON.stringify(this.state.groupData)));
        let activePages = this.selectedPageIds;
        if (!activePages.length) {
            activePages = this.state.focusedPage;
            this.state.focusedPage = false;
        }
        for (const group of fileGroups) {
            group.pageIds = group.pageIds.filter((page) => activePages.includes(page));
        }
        const newFiles = fileGroups.filter((group) => group.pageIds.length > 0);
        for (const newFile of newFiles) {
            newFile.new_pages = [];
            for (const pageId of newFile.pageIds) {
                const fileId = this.state.pages[pageId].fileId;
                const file = this._newFiles[fileId];
                const old_file_type = file.type;
                const old_file_index =
                    old_file_type === "file" ? fileIds.indexOf(fileId) : file.documentId;
                newFile.new_pages.push({
                    old_file_type,
                    old_file_index,
                    old_page_number: this.state.pages[pageId].localPageNumber,
                });
            }
            delete newFile.pageIds;
        }
        // When splitting a file we want them displayed in the same order as they were in the file.
        newFiles.reverse();
        // Http request
        const document = this.props.documents[0];
        const data = new FormData();
        data.append("csrf_token", odoo.csrf_token);
        for (const file of files) {
            data.append("ufile", file);
        }
        data.append("new_files", JSON.stringify(newFiles));
        data.append("archive", this.state.archive);
        data.append(
            "vals",
            JSON.stringify({
                folder_id: document.folder_id[0],
                tag_ids: document.tag_ids.currentIds,
                owner_id: document.owner_id[0],
                partner_id: document.partner_id[0],
                active: this.state.keepDocument,
            })
        );
        const response = await fetch("/documents/pdf_split", {
            method: "post",
            body: data,
        });
        return response.json();
    }
    /**
     * @private
     * @param {String} groupId
     */
    _removeGroup(groupId) {
        if (this.state.groupData[groupId].pageIds.length > 0) {
            return;
        }
        for (const pageId in this.state.pages) {
            const page = this.state.pages[pageId];
            if (page.groupId === groupId) {
                page.groupId = false;
            }
        }
        this.state.groupIds = this.state.groupIds.filter(
            (listedGroupId) => listedGroupId !== groupId
        );
        delete this.state.groupData[groupId];
        this.state.numberOfPages = this.sortedPagesIds.length;
    }
    /**
     * @private
     * @param {String} pageId
     * @param {Object} [param1]
     * @param {boolean} [param1.fromFile] whether to remove page from the file, in which case
     * the file will be removed if none of its pages are used.
     */
    _removePage(pageId, { fromFile } = {}) {
        const page = this.state.pages[pageId];
        if (!page) {
            return;
        }
        const pageIds = this.state.groupData[page.groupId].pageIds;
        this.state.groupData[page.groupId].pageIds = pageIds.filter((number) => number !== pageId);
        if (page.groupId) {
            this._removeGroup(page.groupId);
        }
        page.groupId = false;
        if (fromFile) {
            const selectedPageIds = this._newFiles[page.fileId].selectedPageIds;
            this._newFiles[page.fileId].selectedPageIds = selectedPageIds.filter(
                (number) => number !== pageId
            );
            if (this._newFiles[page.fileId].selectedPageIds.length === 0) {
                this._removeFile(page.fileId);
            }
            page.fileId = false;
        }
        this.state.numberOfPages = this.sortedPagesIds.length;
    }
    /**
     * @private
     * @param {String} fileId
     */
    _removeFile(fileId) {
        for (const pageId of this._newFiles[fileId].pageIds) {
            delete this.state.pageCanvases[pageId];
            delete this.state.pages[pageId];
        }
        delete this._newFiles[fileId];
        this.state.numberOfPages = this.sortedPagesIds.length;
    }
    /**
     * use to remove .pdf extention from file name
     * @private
     * @param {String} name
     */
    _removePdfExtension(name) {
        return name.replace(/\.pdf$/gi, "");
    }
    /**
     * Opens the exit dialog
     * @private
     */
    _exitSplitTools(formerTargetCallback = () => {}) {
        this.dialog.add(ExitSplitToolsDialog, {
            isEmbeddedActionApplied: this._embeddedActionApplied,
            onDeleteRemainingPages: async () => {
                await this.props.close();
                formerTargetCallback();
            },
            onGatherRemainingPages: async () => {
                await this._exitByGatheringRemainingPages();
                formerTargetCallback();
            },
            close: () => {},
        });
    }
    /**
     * Gather the remaining pages so they are kept into one document that is sent to the backend
     * @private
     */
    async _exitByGatheringRemainingPages() {
        const allPages = this.sortedPagesIds;
        this.state.groupData = {};
        this.state.groupIds = [];
        this._createGroup({
            name: this.state.fileName ? _t("%s (remaining pages)", this.state.fileName) : _t("Remaining Pages"),
            pageIds: allPages,
            isSelected: true
        });
        await this._applyChanges();
    }
    /**
     * Adapt the scroll of the page viewer in order to keep the focused page visible
     * @private
     */
    _keepFocusedPageInScreen() {
        const card = document.querySelector(`[data-id=${this.state.focusedPage}]`);
        const focusedCardCoordinates = card.getBoundingClientRect();
        const pageViewerCoordinates = this.pageViewer.el.getBoundingClientRect();
        const bottomDifference = focusedCardCoordinates.bottom - pageViewerCoordinates.bottom;
        const topDifference = focusedCardCoordinates.top - pageViewerCoordinates.top;
        // 60 and 10 are harcoded values to improve the UI when scrolling.
        if (bottomDifference > 0) {
            this.pageViewer.el.scrollBy(0, bottomDifference + 60);
        }
        if (topDifference < 0) {
            this.pageViewer.el.scrollBy(0, topDifference - 10);
        }
    }

    //----------------------------------------------------------------------
    // Keyboard events and handlers
    //----------------------------------------------------------------------

    /**
     * On shift pressed, the focused page is selected
     * @private
     * @param {Event} ev
     */
    _onShiftDown(ev) {
        if (document.activeElement.classList.contains("o_pdf_name_input")) {
            ev.stopPropagation();
            return;
        }
        if (
            ev.key === "Shift" &&
            !ev.metaKey &&
            !ev.ctrlKey &&
            !ev.altKey &&
            !this.state.viewedPage &&
            this.state.focusedPage
        ) {
            this.state.pages[this.state.focusedPage].isSelected =
                !this.state.pages[this.state.focusedPage].isSelected;
        }
    }
    /**
     * Focus next targetted page
     * @private
     * @param {String} direction
     * @param {Boolean} doSelect
     */
    _focusNextPage(direction, doSelect) {
        if (this.state.viewedPage) {
            if (direction === "left") {
                this.onClickPrevious();
            }
            if (direction === "right") {
                this.onClickNext();
            }
            return;
        }
        if (this.state.focusedPage) {
            const sortedPagesIds = this.sortedPagesIds;
            let nextFocusedPageId;
            if (!sortedPagesIds.includes(this.state.focusedPage)) {
                nextFocusedPageId = sortedPagesIds[0];
            } else {
                const indexFocusedPage = sortedPagesIds.indexOf(this.state.focusedPage);
                const numberPerLine = this._computeCardsPerLine();
                const shift = { right: 1, left: -1, down: numberPerLine, up: -numberPerLine }[direction];
                nextFocusedPageId = sortedPagesIds[indexFocusedPage + shift];
            }
            if (nextFocusedPageId) {
                if (doSelect) {
                    this.state.pages[this.state.focusedPage].isSelected =
                        !this.state.pages[nextFocusedPageId].isSelected;
                    this.state.pages[nextFocusedPageId].isSelected = true;
                }
                this.state.focusedPage = nextFocusedPageId;
            }
        } else if (this.state.lastSelectedPage) {
            this.state.focusedPage = this.state.lastSelectedPage;
            this._focusNextPage(direction, doSelect);
        } else {
            this.state.focusedPage = this.sortedPagesIds[0];
            if (doSelect) {
                this.state.pages[this.state.focusedPage].isSelected =
                    !this.state.pages[this.state.focusedPage].isSelected;
            }
        }
        this._keepFocusedPageInScreen();
    }
    /**
     * Focus the first page of the next tragetted group
     * @private
     * @param {String} direction
     */
    _focusNextGroup(direction) {
        if (this.state.viewedPage) {
            return;
        }
        if (this.state.focusedPage) {
            const index = this.state.groupIds.indexOf(
                this.state.pages[this.state.focusedPage].groupId
            );
            const shift = direction === "right" ? 1 : -1;
            const nextNeigbor = this.state.groupData[this.state.groupIds[index + shift]];
            if (nextNeigbor) {
                this.state.focusedPage = nextNeigbor.pageIds[0];
            }
        } else if (this.state.lastSelectedPage) {
            this.state.focusedPage = this.state.lastSelectedPage;
            this._focusNextGroup(direction);
        } else {
            this.state.focusedPage = this.sortedPagesIds[0];
        }
        this._keepFocusedPageInScreen();
    }
    /**
     * Opens or closes the previewer
     * @private
     */
    _togglePreviewer() {
        if (this.state.focusedPage && !this.state.viewedPage) {
            this.onClickPage(this.state.focusedPage);
        }
        if (this.state.focusedPage && this.state.viewedPage) {
            this._onPushExit();
        }
    }
    /**
     * On space key pressed, toogles the focused page
     * @private
     */
    _spaceKeySelect() {
        if (this.state.focusedPage && !this.state.viewedPage) {
            this.state.pages[this.state.focusedPage].isSelected =
                !this.state.pages[this.state.focusedPage].isSelected;
        }
    }
    /**
     * select all the pages from focused page until beginning/end
     * of the group according to the arrow key pressed
     * @private
     * @param {String} direction
     */
    _selectUntilSplit(direction) {
        if (this.state.viewedPage) {
            return;
        }
        if (this.state.focusedPage) {
            const groupData =
                this.state.groupData[this.state.pages[this.state.focusedPage].groupId];
            const pageIndex = groupData.pageIds.indexOf(this.state.focusedPage);
            const pagesToSelect =
                direction === "right"
                    ? groupData.pageIds.slice(pageIndex, groupData.pageIds.length)
                    : groupData.pageIds.slice(0, pageIndex + 1);
            const toggleSelectBool = pagesToSelect.every(
                (pageId) => this.state.pages[pageId].isSelected
            );
            for (const pageId of pagesToSelect) {
                this.state.pages[pageId].isSelected = !toggleSelectBool;
            }
        } else if (this.state.lastSelectedPage) {
            this.state.focusedPage = this.state.lastSelectedPage;
            this._selectUntilSplit(direction);
        } else {
            this.state.focusedPage = this.sortedPagesIds[0];
        }
    }
    /**
     * (De)select all active pages
     * @private
     */
    _selectAll() {
        if (this.state.viewedPage) {
            return;
        }
        const allSelected = this.allSelected;
        for (const page of Object.values(this.state.pages)) {
            page.isSelected = !allSelected;
        }
    }
    /**
     * Exit key pressing behaviour :
     * - Exit previewer
     * - Deselect pages
     * - Loose focus
     * - Exit split tools
     * @private
     */
    _onPushExit() {
        // If we are in the previewer, exit the previewer and focus on previewed page
        if (this.state.viewedPage) {
            this.state.focusedPage = this.state.viewedPage;
            this.previewCanvas = undefined;
            this.state.viewedPage = undefined;
            return;
        }
        // Deselect selected pages
        if (this.selectedPageIds.length) {
            this._unSelectPages();
            return;
        }
        // If one page is focus, loose the focus
        if (this.state.focusedPage) {
            this.state.focusedPage = undefined;
            return;
        }
        this._exitSplitTools();
    }

    //--------------------------------------------------------------------------
    // Click events and handlers
    //--------------------------------------------------------------------------
    /**
     * @private
     * @param {Event} ev
     */
    _onMouseDown(ev) {
        if (
            ev.target.closest(".o_pdf_page") ||
            ev.target.closest(".o_page_splitter_wrapper") ||
            ev.target.closest(".o_documents_pdf_manager_top_bar") ||
            ev.target.closest(".o_main_navbar") ||
            ev.target.closest(".o_documents_pdf_page_preview") ||
            ev.target.closest(".o_pdf_group_name_block") ||
            ev.button !== 0 // Main button pressed, usually the left button or the un-initialized state
        ) {
            return;
        }
        this._selectionX = ev.pageX;
        this._selectionY = ev.pageY - 40;
        this._selectionScrollTop = this.pageViewer.el.scrollTop;
        this._selectionScrollLeft = this.pageViewer.el.scrollLeft;
        this.state.selectionBoxArgs["left"] = this._selectionX + "px";
        this.state.selectionBoxArgs["top"] = this._selectionY + "px";
        this.state.selectionBoxArgs["width"] = 0 + "px";
        this.state.selectionBoxArgs["height"] = 0 + "px";
        this.state.isSelecting = true;
        if (!ev.ctrlKey && !ev.metaKey && !ev.shiftKey) {
            if (!this.selectedPageIds.length) {
                this.state.focusedPage = undefined;
            }
            this.state.edit = false;
            this._unSelectPages();
        }
    }
    /**
     * On mouse move, the selection area expends according the cursor position
     * If selection area enters into a page, the latter is selected except if shift key is pressed.
     * In this case, it is unSelected
     * @private
     * @param {Event} ev
     */
    _onMouseMove(ev) {
        if (!this.state.isSelecting) {
            return;
        }
        this.state.focusedPage = false;
        const x = ev.pageX;
        const y = ev.pageY - 40;
        const scrollTopDiff = this.pageViewer.el.scrollTop - this._selectionScrollTop;
        const scrollLeftDiff = this.pageViewer.el.scrollLeft - this._selectionScrollLeft;
        this.state.selectionBoxArgs["left"] =
            x - this._selectionX + scrollLeftDiff < 0
                ? x + "px"
                : this._selectionX - scrollLeftDiff + "px";
        this.state.selectionBoxArgs["top"] =
            y - this._selectionY + scrollTopDiff < 0
                ? y + "px"
                : this._selectionY - scrollTopDiff + "px";
        this.state.selectionBoxArgs["width"] =
            Math.abs(x - (this._selectionX - scrollLeftDiff)) + "px";
        this.state.selectionBoxArgs["height"] =
            Math.abs(y - (this._selectionY - scrollTopDiff)) + "px";

        const boxCoordinates = this.selectionBox.el.getBoundingClientRect();
        const boxTop = boxCoordinates.top;
        const boxBottom = boxTop + boxCoordinates.height;
        const boxLeft = boxCoordinates.left;
        const boxRight = boxLeft + boxCoordinates.width;
        const cards = document.querySelectorAll(".o_pdf_page");
        for (const card of cards) {
            const cardCoordinates = card.getBoundingClientRect();
            const cardTop = cardCoordinates.top;
            const cardBottom = cardTop + cardCoordinates.height;
            const cardLeft = cardCoordinates.left;
            const cardRight = cardLeft + cardCoordinates.width;

            if (
                boxLeft < cardRight &&
                boxRight > cardLeft &&
                boxTop < cardBottom &&
                boxBottom > cardTop
            ) {
                this.state.pages[card.dataset.id].isSelected = !ev.shiftKey;
            } else if (!ev.metaKey && !ev.ctrlKey && !ev.shiftKey) {
                this.state.pages[card.dataset.id].isSelected = false;
            }
        }
    }
    /**
     * On mouse up, former select pages are unSelected except if ctrl/shift key is pressed
     * If no active pages, selected pages are deselected
     * @private
     */
    _onMouseUp() {
        this.state.isSelecting = false;
    }
    /**
     * @public
     * @param {number} actionId
     */
    onClickEmbeddedAction(actionId) {
        this._applyChanges(actionId);
    }
    /**
     * @public
     */
    onClickSplit() {
        this.state.keepDocument = true;
        this._applyChanges();
    }
    /**
     * @public
     * @param {MouseEvent} ev
     */
    onClickArchive(ev) {
        ev.target.blur();
        this.state.archive = !this.state.archive;
    }
    /**
     * @public
     */
    onClickGlobalAdd() {
        this.addFileInput.el.click();
    }
    /**
     * @public
     */
    async onArchive() {
        let pagesToDelete = this.selectedPageIds;
        if (pagesToDelete.length === 0 && !this.state.focusedPage && !this.state.viewedPage) {
            this._displayErrorNotification(_t("No document has been selected"));
            return;
        }
        const sortedPagesIds = this.sortedPagesIds;
        let messageInput = _t("Are you sure that you want to delete the selected page(s)");
        let nextFocusedPageId = pagesToDelete.includes(this.state.focusedPage)
            ? false
            : this.state.focusedPage;
        if (
            pagesToDelete.length === 0 ||
            this.state.viewedPage ||
            (this.state.focusedPage && !pagesToDelete.includes(this.state.focusedPage))
        ) {
            // A previewed page is always focused
            pagesToDelete = [this.state.focusedPage];
            messageInput = this.state.viewedPage
                ? _t("Are you sure that you want to delete this page ?")
                : _t("Are you sure that you want to delete the focused page ?");
            const focusedPageIndex = sortedPagesIds.indexOf(this.state.focusedPage);
            if (focusedPageIndex + 1 < sortedPagesIds.length) {
                nextFocusedPageId = sortedPagesIds[focusedPageIndex + 1];
            } else if (focusedPageIndex - 1 >= 0) {
                nextFocusedPageId = sortedPagesIds[focusedPageIndex - 1];
            } else {
                nextFocusedPageId = undefined;
            }
        }
        this.dialog.add(ConfirmationDialog, {
            body: messageInput,
            confirm: async () => {
                for (const pageId of pagesToDelete) {
                    this._removePage(pageId, { fromFile: true });
                }
                if (this.state.numberOfPages === 0) {
                    await this.props.onProcessDocuments({ isForcingDelete: true });
                    await this.props.close();
                }
                this._displayNumberDeletedPages(pagesToDelete.length);
                this.state.focusedPage = nextFocusedPageId;
                if (this.state.viewedPage && nextFocusedPageId) {
                    await this.onClickPage(nextFocusedPageId);
                } else {
                    this.state.viewedPage = undefined;
                }
            },
            cancel: () => {},
        });
    }
    /**
     * @public
     * @param {MouseEvent} ev
     */
    async onFileInputChange(ev) {
        this.state.fileName = "";
        if (!ev.target.files.length) {
            return;
        }
        const files = ev.target.files;
        for (const file of files) {
            await this._addFile(file.name, { file });
        }
        ev.target.value = null;
    }
    /**
     * @public
     */
    onClickExit() {
        this._exitSplitTools();
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onOutsideClick(ev) {
        if (
            (!this._exitSplitToolsClick &&
                (ev.target.closest(".dropdown-item") || ev.target.closest(".o_menu_toggle")) &&
                ev.target.closest(".dropdown-item")?.dataset.menu !== "shortcuts" &&
                ev.target.closest(".dropdown-item")?.dataset.menu !== "settings" &&
                ev.target.closest(".dropdown-item")?.dataset.menu !== "support" &&
                ev.target.closest(".dropdown-item")?.dataset.menu !== "documentation" &&
                !ev.target.closest("[data-dropdown-is-mobile]")) ||
            ev.target.closest(".o_burger_menu_content")
        ) {
            ev.stopPropagation();
            ev.preventDefault();
            this._exitSplitTools(() => {
                this._exitSplitToolsClick = true;
                ev.target.click();
            });
        }
    }
    /**
     * Open the previewer
     * @public
     * @param {String} pageId
     */
    async onClickPage(pageId) {
        this.state.focusedPage = pageId;
        const page = this.state.pageCanvases[pageId].page;
        if (!page) {
            return;
        }
        const previewWrapper = document.querySelector(".o_documents_pdf_page_preview");
        const ratio = 18 / 13;
        const width = previewWrapper.clientWidth - (30 * window.innerWidth) / 100;
        this.previewCanvas = await this._renderCanvas(toRaw(page), {
            width: width,
            height: width * ratio,
        });
        this.state.viewedPage = pageId;
        const targetGroup = this.state.groupData[this.state.pages[pageId].groupId];
        this.state.viewedPageName =
            targetGroup.name + "-p" + (targetGroup.pageIds.indexOf(pageId) + 1);
        const sortedPagesIds = this.sortedPagesIds;
        this.state.viewedPageIndex = sortedPagesIds.indexOf(pageId);
    }
    /**
     * @public
     */
    async onClickPrevious() {
        if (this.state.viewedPageIndex > 0) {
            await this.onClickPage(this.sortedPagesIds[this.state.viewedPageIndex - 1]);
        }
    }
    /**
     * @public
     */
    async onClickNext() {
        if (this.state.viewedPageIndex < this.state.numberOfPages - 1) {
            await this.onClickPage(this.sortedPagesIds[this.state.viewedPageIndex + 1]);
        }
    }
    /**
     * @public
     * @param {customEvent} ev
     */
    onClickExitPreview(ev) {
        if (
            ev.target.classList.contains("o_documents_pdf_page_preview") ||
            ev.target.closest(".o_close_button")
        ) {
            this.state.focusedPage = this.state.viewedPage;
            this.previewCanvas = undefined;
            this.state.viewedPage = undefined;
        }
    }
    /**
     * select clicked page.
     * If shift key is pressed, trigger the range activation between last clicked page and current page
     * @public
     * @param {String} pageId
     * @param {Boolean} isRangeSelection
     * @param {Boolean} ctrlKey
     */
    onSelectClicked(pageId, isRangeSelection, ctrlKey) {
        this.state.pages[pageId].isSelected = !this.state.pages[pageId].isSelected;
        if (
            isRangeSelection &&
            this.state.lastSelectedPage &&
            this.state.pages[pageId].isSelected
        ) {
            const sortedPagesIds = this.sortedPagesIds;
            const pageIndex = sortedPagesIds.indexOf(pageId);
            const lastSelectedPageIndex = sortedPagesIds.indexOf(this.state.lastSelectedPage);
            const pagesToSelect =
                pageIndex < lastSelectedPageIndex
                    ? sortedPagesIds.slice(pageIndex, lastSelectedPageIndex + 1)
                    : sortedPagesIds.slice(lastSelectedPageIndex, pageIndex + 1);
            for (const pageId of pagesToSelect) {
                this.state.pages[pageId].isSelected = true;
            }
        }
        this.state.lastSelectedPage = pageId;
    }
    /**
     * @public
     * @param {String} pageId
     * @param {String} groupId
     */
    onClickPageSeparator(pageId, groupId) {
        this._pageSeparator(pageId, groupId);
    }
    /**
     * @public
     * @param {String} groupId
     * @param {String} name
     */
    onEditName(groupId, name) {
        this.state.groupData[groupId].name = name || _t("unnamed");
    }
    /**
     * @public
     * @param {customEvent} ev
     */
    onPageDragStart(ev) {
        ev.stopPropagation();
    }
    /**
     * @public
     * @param {String} ev.detail.targetPageId
     * @param {String} ev.detail.pageId
     */
    onPageDrop(targetPageId, pageId) {
        const targetGroupId = this.state.pages[targetPageId].groupId;
        const index = this.state.groupData[targetGroupId].pageIds.indexOf(targetPageId);
        this._addPage(pageId, targetGroupId, { index });
    }
}
