/**
 * @typedef { import("./editor").Editor } Editor
 * @typedef { import("./editor").EditorConfig } EditorConfig
 * @typedef { import("./core/history_plugin").HistoryPlugin } HistoryPlugin
 * @typedef { import("./core/selection_plugin").SelectionPlugin } SelectionPlugin
 * @typedef { import("./core/delete_plugin").DeletePlugin } DeletePlugin
 * @typedef { import("./core/dom_plugin").DomPlugin } DomPlugin
 * @typedef { import("./core/split_plugin").SplitPlugin } SplitPlugin
 * @typedef { import("./core/overlay_plugin").OverlayPlugin } OverlayPlugin
 * @typedef { import("./main/local_overlay_plugin").LocalOverlayPlugin } LocalOverlayPlugin
 * @typedef { import("./main/powerbox/powerbox_plugin").PowerboxPlugin } PowerboxPlugin
 * @typedef { import("./main/link/link_plugin").LinkPlugin } LinkPlugin
 * @typedef { import("./core/sanitize_plugin").SanitizePlugin } SanitizePlugin
 * @typedef { import("./core/format_plugin").FormatPlugin } FormatPlugin
 * @typedef { import("./others/collaboration/collaboration_plugin").CollaborationPlugin } CollaborationPlugin
 * @typedef { import("./others/collaboration/collaboration_odoo_plugin").CollaborationOdooPlugin } CollaborationOdooPlugin
 *
 * @typedef { Object } SharedMethods
 *
 * @property { HistoryPlugin['reset'] } reset
 * @property { HistoryPlugin['makeSavePoint'] } makeSavePoint
 * @property { HistoryPlugin['makeSnapshotStep'] } makeSnapshotStep
 * @property { HistoryPlugin['disableObserver'] } disableObserver
 * @property { HistoryPlugin['enableObserver'] } enableObserver
 * @property { HistoryPlugin['addExternalStep'] } addExternalStep
 * @property { HistoryPlugin['getHistorySteps'] } getHistorySteps
 * @property { HistoryPlugin['historyResetFromSteps'] } historyResetFromSteps
 * @property { HistoryPlugin['serializeSelection'] } serializeSelection
 * @property { HistoryPlugin['getNodeById'] } getNodeById
 * @property { SelectionPlugin['getEditableSelection'] } getEditableSelection
 * @property { SelectionPlugin['getSelectedNodes'] } getSelectedNodes
 * @property { SelectionPlugin['getTraversedNodes'] } getTraversedNodes
 * @property { SelectionPlugin['getTraversedBlocks'] } getTraversedBlocks
 * @property { SelectionPlugin['setSelection'] } setSelection
 * @property { SelectionPlugin['setCursorStart'] } setCursorStart
 * @property { SelectionPlugin['setCursorEnd'] } setCursorEnd
 * @property { SelectionPlugin['extractContent'] } extractContent
 * @property { SelectionPlugin['preserveSelection'] } preserveSelection
 * @property { SelectionPlugin['resetSelection'] } resetSelection
 * @property { SelectionPlugin['getSelectedNodes'] } getSelectedNodes
 * @property { SelectionPlugin['getTraversedNodes'] } getTraversedNodes
 * @property { SelectionPlugin['modifySelection'] } modifySelection
 * @property { FormatPlugin['isSelectionFormat'] } isSelectionFormat
 * @property { LocalOverlayPlugin['makeLocalOverlay'] } makeLocalOverlay
 * @property { PowerboxPlugin['openPowerbox'] } openPowerbox
 * @property { PowerboxPlugin['updatePowerbox'] } updatePowerbox
 * @property { PowerboxPlugin['closePowerbox'] } closePowerbox
 * @property { SanitizePlugin['sanitize'] } sanitize
 * @property { DeletePlugin['deleteRange'] } deleteRange
 * @property { LinkPlugin['createLink'] } createLink
 * @property { LinkPlugin['getOrCreateLink'] } getOrCreateLink
 * @property { LinkPlugin['insertLink'] } insertLink
 * @property { LinkPlugin['getPathAsUrlCommand'] } getPathAsUrlCommand
 * @property { LinkPlugin['linkOptions'] } linkOptions
 * @property { DomPlugin['domInsert'] } domInsert
 * @property { DomPlugin['copyAttributes'] } copyAttributes
 * @property { SplitPlugin['isUnsplittable'] } isUnsplittable
 * @property { SplitPlugin['splitBlock'] } splitBlock
 * @property { SplitPlugin['splitElementBlock'] } splitElementBlock
 * @property { SplitPlugin['splitElement'] } splitElement
 * @property { SplitPlugin['splitSelection'] } splitSelection
 * @property { SplitPlugin['splitAroundUntil'] } splitAroundUntil
 * @property { SplitPlugin['splitTextNode'] } splitTextNode
 * @property { OverlayPlugin['createOverlay'] } createOverlay
 * @property { CollaborationPlugin['onExternalHistorySteps'] } onExternalHistorySteps
 * @property { CollaborationPlugin['historyGetMissingSteps'] } historyGetMissingSteps
 * @property { CollaborationPlugin['setInitialBranchStepId'] } setInitialBranchStepId
 * @property { CollaborationPlugin['getBranchIds'] } getBranchIds
 * @property { CollaborationPlugin['getSnapshotSteps'] } getSnapshotSteps
 * @property { CollaborationPlugin['resetFromSteps'] } resetFromSteps
 * @property { CollaborationOdooPlugin['getPeerMetadata'] } getPeerMetadata
 * @property { ToolbarPlugin['getToolbarInfo'] } getToolbarInfo
 */

export class Plugin {
    static name = "";
    static dependencies = [];
    static shared = [];

    /**
     * @param {Editor['document']} document
     * @param {Editor['editable']} editable
     * @param {SharedMethods} shared
     * @param {Editor['dispatch']} dispatch
     * @param {import("./editor").EditorConfig} config
     * @param {*} services
     */
    constructor(document, editable, shared, dispatch, config, services) {
        /** @type { Document } **/
        this.document = document;
        /** @type { HTMLElement } **/
        this.editable = editable;
        /** @type { EditorConfig } **/
        this.config = config;
        this.services = services;
        /** @type { SharedMethods } **/
        this.shared = shared;
        this.dispatch = dispatch;
        this._cleanups = [];
        this.resources = null; // set before start
    }

    setup() {}

    /**
     * add it here so it is available in tooling
     *
     * @param {string} command
     * @param {any} payload
     * @returns { any }
     */
    dispatch(command, payload) {}

    handleCommand(command) {}

    addDomListener(target, eventName, fn, capture) {
        const handler = fn.bind(this);
        target.addEventListener(eventName, handler, capture);
        this._cleanups.push(() => target.removeEventListener(eventName, handler, capture));
    }

    destroy() {
        for (const cleanup of this._cleanups) {
            cleanup();
        }
    }
}
