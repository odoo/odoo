import { Plugin } from "../plugin";
import { hasTouch } from "@web/core/browser/feature_detection";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";

/**
 * @typedef { Object } PreviewableOperation
 * @property { Function } commit
 * @property { Function } preview
 * @property { Function } revert
 */

/**
 * @typedef { Object } HistoryShared
 * @property { HistoryPlugin['commit'] } commit
 * @property { HistoryPlugin['stash'] } stash
 * @property { HistoryPlugin['unstash'] } unstash
 * @property { HistoryPlugin['undo'] } undo
 * @property { HistoryPlugin['redo'] } redo
 * @property { HistoryPlugin['canUndo'] } canUndo
 * @property { HistoryPlugin['canRedo'] } canRedo
 * @property { HistoryPlugin['stage'] } stage
 * @property { HistoryPlugin['getStaged'] } getStaged
 * @property { HistoryPlugin['apply'] } apply
 * @property { HistoryPlugin['getCommits'] } getCommits
 * @property { HistoryPlugin['reset'] } reset
 * @property { HistoryPlugin['createSnapshotCommit'] } createSnapshotCommit
 * @property { HistoryPlugin['insertRemoteCommit'] } insertRemoteCommit
 * @property { HistoryPlugin['getIsPreviewing'] } getIsPreviewing
 * @property { HistoryPlugin['makePreviewableOperation'] } makePreviewableOperation
 * @property { HistoryPlugin['makePreviewableAsyncOperation'] } makePreviewableAsyncOperation
 * @property { HistoryPlugin['makeSavePoint'] } makeSavePoint
 */
/**
 * Properties are named entries of the commit data (changes) or metadata. Their
 * values are staged in the history draft, then collected into the next commit,
 * after which the draft is cleared. Undefined values are left out of the
 * commit. Staged values are immutable: replace them, don't mutate them. Values
 * that are computed when a commit is created are added by
 * `pending_history_commit_data_processors` and
 * `pending_history_commit_metadata_processors` instead, which run before the
 * properties are collected from the draft. Properties are applied and reverted
 * in resource order.
 */
/**
 * Plugins declare history properties in objects keyed by their ids. These ids
 * are registered in the `HistoryDataProperties` and `HistoryMetadataProperties`
 * interfaces of the "plugins" module: each data property with the signature of
 * its `apply`, each metadata property with the type of its value.
 *
 * @typedef { keyof import("plugins").HistoryDataProperties } HistoryDataPropertyId
 * @typedef { keyof import("plugins").HistoryMetadataProperties } HistoryMetadataPropertyId
 */
/**
 * A data property holds changes, in the commit's `data`: its value is the list
 * of the data passed to `apply`, which applies and stages it. That data must be
 * serializable. `apply` and `revert` receive one of them, to apply it again on
 * redo, and to revert it on undo or when it is discarded. Only the commits in
 * which changes are made hold data: the commits created by the history (undo,
 * redo, restore) replay the data of the commits they revert or reapply.
 *
 * @template { HistoryDataPropertyId } Id
 * @typedef {Object} HistoryDataProperty
 * @property {import("plugins").HistoryDataProperties[Id]} apply
 * @property {(data: HistoryData<Id>) => void} revert
 */
/**
 * The data that the handlers of a data property receive.
 *
 * @template { HistoryDataPropertyId } Id
 * @typedef { Parameters<import("plugins").HistoryDataProperties[Id]>[0] } HistoryData
 */
/** @typedef { { [Id in HistoryDataPropertyId]?: HistoryDataProperty<Id> }[] } history_data_properties */
/**
 * A metadata property describes its commit, in its `metadata` (the selection,
 * for example). Any metadata that a plugin adds to commits is declared as a
 * metadata property. It is not a change: its draft is kept when changes are
 * discarded, and savepoints restore it as is. `apply` and `revert` receive its
 * value when a commit that has one is applied or reverted.
 *
 * @template { HistoryMetadataPropertyId } Id
 * @typedef {Object} HistoryMetadataProperty
 * @property {(value: import("plugins").HistoryMetadataProperties[Id], options: { ensureNewMutations: boolean }) => void} [apply]
 * @property {(value: import("plugins").HistoryMetadataProperties[Id], options: { ensureNewMutations: boolean }) => void} [revert]
 */
/** @typedef { { [Id in HistoryMetadataPropertyId]?: HistoryMetadataProperty<Id> }[] } history_metadata_properties */
/**
 * The value of a property in the draft: the list of its data for a data
 * property, its value for a metadata property.
 *
 * @template { HistoryDataPropertyId | HistoryMetadataPropertyId } Id
 * @typedef { Id extends HistoryDataPropertyId
 *     ? HistoryData<Id>[]
 *     : Id extends HistoryMetadataPropertyId
 *       ? import("plugins").HistoryMetadataProperties[Id]
 *       : never
 * } HistoryStagedValue
 */

/**
 * @typedef { ((commit: HistoryCommit, options: { ensureNewMutations: boolean, restoreSelection: boolean }) => void)[] } on_apply_history_commit_handlers
 * @typedef { ((commit: HistoryCommit) => void)[] } on_committed_to_history_handlers
 * @typedef { (() => void)[] } on_history_commit_restored_handlers
 * @typedef { ((lastCommitUndone: HistoryCommit<"standard" | "redo"> | undefined) => void)[] } on_history_commit_undone_handlers
 * @typedef { ((lastCommitRedone: HistoryCommit<"undo"> | undefined) => void)[] } on_history_commit_redone_handlers
 * @typedef { (() => void)[] } on_history_rebased_handlers
 * @typedef { (() => void)[] } on_history_reset_handlers
 * @typedef { (() => void)[] } on_irreversible_history_commit_applied_handlers
 * @typedef { ((stashedCommit: HistoryCommit<"stash">) => void)[] } on_pending_changes_unstashed_handlers
 * @typedef { ((newCommit: HistoryCommit) => void)[] } on_remote_history_commit_applied_handlers
 * @typedef { ((commit: HistoryCommit, options: { ensureNewMutations: boolean, restoreFocus: boolean }) => void)[] } on_revert_history_commit_handlers
 * @typedef { ((savePoint: HistoryCommit<"savePoint">) => void)[] } on_savepoint_restored_handlers
 * @typedef { (() => void)[] } on_will_invalidate_pending_changes_handlers
 * @typedef { (() => void)[] } on_will_preview_handlers
 * @typedef { (() => void)[] } on_will_rebase_history_handlers
 * @typedef { (() => void)[] } on_will_reset_history_handlers
 *
 * @typedef { ((commit: HistoryCommit) => boolean | undefined)[] } has_history_commit_changes_predicates
 * @typedef { ((commit: HistoryCommit) => boolean | undefined)[] } is_history_commit_reversible_predicates
 *
 * @typedef { ((data: HistoryCommitData, metadata: HistoryCommitMetadata) => HistoryCommitData)[] } pending_history_commit_data_processors
 * @typedef { ((metadata: HistoryCommitMetadata) => HistoryCommitMetadata)[] } pending_history_commit_metadata_processors
 * @typedef { ((data: HistoryCommitData<"savePoint">) => HistoryCommitData<"savePoint">)[] } save_point_history_commit_data_processors
 * @typedef { ((metadata: HistoryCommitMetadata<"savePoint">) => HistoryCommitMetadata<"savePoint">)[] } save_point_history_commit_metadata_processors
 * @typedef { ((data: HistoryCommitData<"standard">) => HistoryCommitData<"standard">)[] } snapshot_history_commit_data_processors
 * @typedef { ((metadata: HistoryCommitMetadata<"standard"> & { author_timestamp: number }) => HistoryCommitMetadata<"standard">)[] } snapshot_history_commit_metadata_processors
 */

export const COMMIT_DEBOUNCE_DELAY = 250;
export const HISTORY_COMMIT_TYPES = /** @type {const} */ ({
    STANDARD: "standard",
    UNDO: "undo",
    REDO: "redo",
    RESTORE: "restore",
    SAVEPOINT: "savePoint",
    STASH: "stash",
});

export class HistoryPlugin extends Plugin {
    static id = "history";
    static dependencies = ["domReferenceMap"];
    static shared = [
        "commit",
        "stash",
        "unstash",
        "undo",
        "redo",
        "canUndo",
        "canRedo",
        "stage",
        "getStaged",
        "apply",
        "getCommits",
        "reset",
        "createSnapshotCommit",
        "insertRemoteCommit",

        // Preview
        "getIsPreviewing",
        "makePreviewableOperation",
        "makePreviewableAsyncOperation",
        "makeSavePoint",
    ];
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "historyUndo",
                description: _t("Undo"),
                icon: "undo",
                run: this.undo.bind(this),
            },
            {
                id: "historyRedo",
                description: _t("Redo"),
                icon: "redo",
                run: this.redo.bind(this),
            },
        ],
        ...(hasTouch() && {
            toolbar_groups: withSequence(5, { id: "historyMobile" }),
            toolbar_items: [
                {
                    id: "undo",
                    groupId: "historyMobile",
                    commandId: "historyUndo",
                    isDisabled: () => !this.canUndo(),
                    namespaces: ["compact", "expanded"],
                },
                {
                    id: "redo",
                    groupId: "historyMobile",
                    commandId: "historyRedo",
                    isDisabled: () => !this.canRedo(),
                    namespaces: ["compact", "expanded"],
                },
            ],
        }),
        shortcuts: [
            { hotkey: "control+z", commandId: "historyUndo", global: true },
            { hotkey: "control+y", commandId: "historyRedo", global: true },
            { hotkey: "control+shift+z", commandId: "historyRedo", global: true },
        ],

        on_editor_started_handlers: () => {
            this.reset();
        },
        on_will_reset_history_handlers: this.resetAuthorTimestamp.bind(this),
        on_committed_to_history_handlers: withSequence(0, () => {
            this.resetAuthorTimestamp();
            this.stagedData = {};
        }),

        // Properties

        // Data can depend on attributes restored by the DOM observer. Apply it
        // after DOM mutations, before selection restoration (100).
        on_apply_history_commit_handlers: withSequence(20, (commit, { ensureNewMutations }) => {
            this.applyDataProperties(commit);
            for (const [id, { apply }] of this.metadataProperties) {
                if (id in commit.metadata) {
                    apply?.(commit.metadata[id], { ensureNewMutations });
                }
            }
        }),
        on_revert_history_commit_handlers: withSequence(20, (commit, { ensureNewMutations }) => {
            this.revertDataProperties(commit);
            for (const [id, { revert }] of this.metadataProperties) {
                if (id in commit.metadata) {
                    revert?.(commit.metadata[id], { ensureNewMutations });
                }
            }
        }),
        on_savepoint_restored_handlers: withSequence(20, (savePoint) => {
            for (const [id, { apply }] of this.dataProperties) {
                if (savePoint.data[id]) {
                    // The discarded data is applied and staged again.
                    this.stage(id, savePoint.data[id]);
                    for (const data of savePoint.data[id]) {
                        apply(data);
                    }
                }
            }
            for (const id of this.metadataProperties.keys()) {
                this.stagedData[id] = savePoint.metadata[id];
            }
        }),
        on_pending_changes_unstashed_handlers: (stashedCommit) => {
            for (const id of this.dataProperties.keys()) {
                if (stashedCommit.data[id]) {
                    // Applying the stash did not stage its data.
                    this.stage(id, stashedCommit.data[id]);
                }
            }
        },
        has_history_commit_changes_predicates: (commit) => {
            if (this.hasDataProperties(commit)) {
                return true;
            }
        },
    };

    setup() {
        this.stagedData = {};
        /** @type {Map<HistoryDataPropertyId, HistoryDataProperty<HistoryDataPropertyId>>} */
        this.dataProperties = new Map();
        /** @type {Map<HistoryMetadataPropertyId, HistoryMetadataProperty<HistoryMetadataPropertyId>>} */
        this.metadataProperties = new Map();
        for (const [resourceId, properties] of [
            ["history_data_properties", this.dataProperties],
            ["history_metadata_properties", this.metadataProperties],
        ]) {
            for (const propertiesById of this.getResource(resourceId)) {
                for (const [id, property] of Object.entries(propertiesById)) {
                    if (this.dataProperties.has(id) || this.metadataProperties.has(id)) {
                        throw new Error(`Duplicate history property: ${id}`);
                    }
                    properties.set(id, property);
                }
            }
        }
        this.resetAuthorTimestamp();
        this._onKeyupResetContenteditableNodes = [];
        this.addDomListener(this.document, "beforeinput", this.onDocumentBeforeInput.bind(this));
        this.addDomListener(this.document, "input", this.onDocumentInput.bind(this));
        /** @type { HistoryCommit<"stash">[] } */
        this.currentStash = [];
    }

    /**
     * Reset the history. If commits are provided, apply them into the blank DOM
     * of the editor and start the history with these commits.
     *
     * @param { HistoryCommit[] } [commits]
     */
    reset(commits) {
        this.stagedData = {};
        this.trigger("on_will_reset_history_handlers");
        this.commits = commits || [this.createSnapshotCommit()];
        /** @type {Set<HistoryCommitId>} Commits reverted by undo/redo operations */
        this.revertedCommits = new Set();
        /** @type {Set<HistoryCommitId>} Commits reverted by restoring to a save point */
        this.discardedCommits = new Set();
        if (commits) {
            this.trigger("on_will_rebase_history_handlers");
            this.editable.replaceChildren();
            commits.forEach(this.applyCommit.bind(this));
            this.trigger("on_history_rebased_handlers");
        }
        this.trigger("on_history_reset_handlers");
    }

    // ===============
    // Core public API
    // ===============

    /**
     * Create a commit from the draft and write it to history.
     *
     * @param { HistoryCommitMetadata<"standard"> } [initialMetadata = {}]
     * @returns { HistoryCommit<"standard"> | false }
     */
    commit(initialMetadata = {}) {
        // Set the type of the commit here. That way, the state of undo and redo
        // is truly accessible when executing the `onChange` callback. It is
        // useful for external components if they execute `can(Undo|Redo)`.
        const { data, metadata } = this.processCommit({
            batchable: false, // possibly overridden by `initialMetadata`
            ...initialMetadata,
            author_timestamp: this.authorTimestamp,
        });
        const commit = new HistoryCommit({ data, metadata });
        return this.appendCommit(commit);
    }

    /**
     * Undo the last undo-able batch of commits.
     */
    undo() {
        this.reverse(HISTORY_COMMIT_TYPES.UNDO);
    }

    /**
     * Redo the last redo-able batch of commits.
     */
    redo() {
        this.reverse(HISTORY_COMMIT_TYPES.REDO);
    }

    /**
     * Gather all staged changes and add them to the stash for later use. Then
     * discard those changes.
     */
    stash() {
        const stashCommit = new HistoryCommit({
            type: HISTORY_COMMIT_TYPES.STASH,
            ...this.processCommit(),
        });
        this.currentStash.push(stashCommit);
        this.discardStagedChanges();
    }

    /**
     * Take the commit at the given index in the stash (or the last one by
     * default), apply its changes and remove it from the stash.
     *
     * /!\ Conflicts may occur and are not handled so use with care.
     *
     * @param { number } [index = -1]
     */
    unstash(index = -1) {
        if (this.currentStash.length > index) {
            const stashedCommit = this.currentStash.splice(index, 1)[0];
            this.applyCommit(stashedCommit);
            this.trigger("on_pending_changes_unstashed_handlers", stashedCommit);
        }
    }

    /**
     * Stage the value of a property in the draft, to be collected into the next
     * commit. Staged values are immutable: replace them, don't mutate them.
     *
     * @template { HistoryDataPropertyId | HistoryMetadataPropertyId } Id
     * @param {Id} id The registered property.
     * @param {HistoryStagedValue<Id>} value
     */
    stage(id, value) {
        this.getProperty(id);
        this.stagedData[id] = value;
    }

    /**
     * Return the value of a property in the draft.
     *
     * @template { HistoryDataPropertyId | HistoryMetadataPropertyId } Id
     * @param {Id} id The registered property.
     * @returns {HistoryStagedValue<Id> | undefined} The staged value, undefined if none.
     */
    getStaged(id) {
        this.getProperty(id);
        return this.stagedData[id];
    }

    /**
     * Look up a registered history property.
     *
     * @param {HistoryDataPropertyId | HistoryMetadataPropertyId} id
     * @returns {HistoryDataProperty<HistoryDataPropertyId> | HistoryMetadataProperty<HistoryMetadataPropertyId>}
     * @throws {Error} If the property is not registered.
     */
    getProperty(id) {
        const property = this.dataProperties.get(id) ?? this.metadataProperties.get(id);
        if (!property) {
            throw new Error(`Unknown history property: ${id}`);
        }
        return property;
    }

    /**
     * Discard the pending changes of the draft: notify plugins to discard
     * theirs, then revert the data of the data properties and clear it.
     * Metadata properties keep their draft.
     *
     * @returns {void}
     */
    discardStagedChanges() {
        this.trigger("on_will_invalidate_pending_changes_handlers");
        for (const [id, { revert }] of this.dataProperties) {
            const stagedData = this.stagedData[id] ?? [];
            delete this.stagedData[id];
            for (const data of stagedData.toReversed()) {
                revert(data);
            }
        }
    }

    /**
     * Apply data of a data property and stage it, to be replayed with the
     * commit it ends up in: applied again on redo, reverted on undo.
     *
     * @template { HistoryDataPropertyId } Id
     * @param {Id} id The registered data property.
     * @param {HistoryData<Id>} data Serializable data passed to the property's handlers.
     * @returns {ReturnType<import("plugins").HistoryDataProperties[Id]>} The value returned
     *          by the property's `apply` handler.
     */
    apply(id, data) {
        const property = /** @type {HistoryDataProperty<Id>} */ (this.dataProperties.get(id));
        if (!property) {
            throw new Error(`Unknown history data property: ${id}`);
        }
        data = structuredClone(data);
        this.stage(id, [...(this.stagedData[id] ?? []), data]);
        return property.apply(data);
    }

    /**
     * Apply the data properties of the given commit. A commit created by the
     * history holds none: it applies those of the commits it replays. A commit
     * that is not in the history (undefined) has no data to apply.
     *
     * @param {HistoryCommit | undefined} commit
     * @returns {void}
     */
    applyDataProperties(commit) {
        if (!commit) {
            return;
        }
        switch (commit.type) {
            case HISTORY_COMMIT_TYPES.UNDO:
            case HISTORY_COMMIT_TYPES.REDO:
                this.revertDataProperties(this.getCommit(commit.metadata.related_commit_id));
                break;
            case HISTORY_COMMIT_TYPES.RESTORE:
                for (const id of commit.metadata.reverted_commit_ids) {
                    this.revertDataProperties(this.getCommit(id));
                }
                for (const id of commit.metadata.reapplied_commit_ids) {
                    this.applyDataProperties(this.getCommit(id));
                }
                break;
            default:
                for (const [id, { apply }] of this.dataProperties) {
                    for (const data of commit.data[id] ?? []) {
                        apply(data);
                    }
                }
        }
    }

    /**
     * Revert the data properties of the given commit: the inverse of
     * `applyDataProperties`.
     *
     * @param {HistoryCommit | undefined} commit
     * @returns {void}
     */
    revertDataProperties(commit) {
        if (!commit) {
            return;
        }
        switch (commit.type) {
            case HISTORY_COMMIT_TYPES.UNDO:
            case HISTORY_COMMIT_TYPES.REDO:
                this.applyDataProperties(this.getCommit(commit.metadata.related_commit_id));
                break;
            case HISTORY_COMMIT_TYPES.RESTORE:
                for (const id of commit.metadata.reapplied_commit_ids.toReversed()) {
                    this.revertDataProperties(this.getCommit(id));
                }
                for (const id of commit.metadata.reverted_commit_ids.toReversed()) {
                    this.applyDataProperties(this.getCommit(id));
                }
                break;
            default:
                for (const [id, { revert }] of this.dataProperties) {
                    for (const data of (commit.data[id] ?? []).toReversed()) {
                        revert(data);
                    }
                }
        }
    }

    /**
     * Return whether the given commit has data properties, directly or through
     * the commits it replays.
     *
     * @param {HistoryCommit | undefined} commit
     * @returns {boolean}
     */
    hasDataProperties(commit) {
        if (!commit) {
            return false;
        }
        switch (commit.type) {
            case HISTORY_COMMIT_TYPES.UNDO:
            case HISTORY_COMMIT_TYPES.REDO:
                return this.hasDataProperties(this.getCommit(commit.metadata.related_commit_id));
            case HISTORY_COMMIT_TYPES.RESTORE:
                return [
                    ...commit.metadata.reverted_commit_ids,
                    ...commit.metadata.reapplied_commit_ids,
                ].some((id) => this.hasDataProperties(this.getCommit(id)));
            default:
                return [...this.dataProperties.keys()].some((id) => commit.data[id]?.length);
        }
    }

    /**
     * Return the commit of the history with the given id. A commit can be
     * missing: a history reset from a collaboration snapshot starts after it.
     *
     * @param {HistoryCommitId} id
     * @returns {HistoryCommit | undefined}
     */
    getCommit(id) {
        return this.commits.findLast((commit) => commit.id === id);
    }

    /**
     * Return a copy of the list of commits recorded in history.
     *
     * @returns { HistoryCommit[] }
     */
    getCommits() {
        return [...this.commits];
    }

    // ====================
    // Commit data handling
    // ====================

    /**
     * Return the data and metadata of a new commit, made of any pending data
     * and metadata in plugins that subscribe to
     * `pending_history_commit_data_processors` and
     * `pending_history_commit_metadata_processors`, which can stage their
     * pending changes, then of the properties collected from the draft, as well
     * as metadata provided by this plugin.
     *
     * @template { WritableHistoryCommitType } [T="standard"]
     * @param { HistoryCommitMetadata<T> } [metadata = {}]
     * @returns { { data: HistoryCommitData<T>, metadata: HistoryCommitMetadata<T> } }
     */
    processCommit(metadata = {}) {
        // Set the timestamp of the commit or keep the timestamp of the commit
        // it reverts:
        metadata.commit_timestamp ??= Date.now();
        metadata.author_timestamp ??= this.authorTimestamp;
        metadata.previous_commit_id = this.commits?.at(-1)?.id;
        const data = this.processThrough("pending_history_commit_data_processors", {}, metadata);
        metadata = this.processThrough("pending_history_commit_metadata_processors", metadata);
        this.collectStagedProperties(data, metadata);
        return { data, metadata };
    }

    /**
     * Add the values of the properties staged in the draft to the given data
     * and metadata.
     *
     * @param { HistoryCommitData } data
     * @param { HistoryCommitMetadata } metadata
     * @returns { void }
     */
    collectStagedProperties(data, metadata) {
        for (const [properties, values] of [
            [this.dataProperties, data],
            [this.metadataProperties, metadata],
        ]) {
            for (const id of properties.keys()) {
                if (this.stagedData[id] !== undefined) {
                    values[id] = this.stagedData[id];
                }
            }
        }
    }

    /**
     * Reset the staged timestamp.
     */
    resetAuthorTimestamp() {
        this.authorTimestamp = Date.now();
    }

    // =======================
    // Commit creation/writing
    // =======================

    /**
     * Record the given commit in the history, if it contains any changes.
     * Otherwise, return `false`.
     *
     * @template { WritableHistoryCommitType } T
     * @param { HistoryCommit<T> } commit
     * @returns { HistoryCommit<T> | false }
     */
    appendCommit(commit) {
        // @todo @phoenix should we allow to pause the making of a commit?
        // if (!this.commitsActive) {
        //     return;
        // }
        // @todo @phoenix link zws plugin
        // this._resetLinkZws();
        // @todo @phoenix sanitize plugin
        // this.sanitize();
        if (this.checkPredicates("has_history_commit_changes_predicates", commit) ?? false) {
            this.commits.push(commit);
            // @todo @phoenix add this in the linkzws plugin.
            // this._setLinkZws();
            // Notify of changes.
            this.trigger("on_committed_to_history_handlers", commit);
            this.config.onChange?.({ isPreviewing: this.isPreviewing });
            return commit;
        } else {
            return false;
        }
    }

    /**
     * Create and return a "snapshot" commit.
     *
     * @returns { HistoryCommit<"standard"> }
     */
    createSnapshotCommit() {
        /** @type { HistoryCommitData<"standard"> } */
        const data = this.processThrough("snapshot_history_commit_data_processors", {});
        /** @type { HistoryCommitMetadata<"standard"> } */
        const metadata = this.processThrough("snapshot_history_commit_metadata_processors", {
            author_timestamp: this.authorTimestamp,
        });
        return new HistoryCommit({ id: this.commits?.at(-1)?.id, data, metadata });
    }

    // ===========================
    // Commit application/reversal
    // ===========================

    /**
     * Delegate the application of the changes in the given commit to the
     * plugins that subscribe to `on_apply_history_commit_handlers`.
     *
     * @param { HistoryCommit } commit
     * @param { Object } [params = {}]
     * @param { boolean } [params.ensureNewMutations = false]
     * @param { boolean } [params.restoreSelection = false]
     */
    applyCommit(commit, { ensureNewMutations = false, restoreSelection = false } = {}) {
        this.trigger("on_apply_history_commit_handlers", commit, {
            ensureNewMutations,
            restoreSelection,
        });
    }

    /**
     * Delegate the reversal of the changes in the given commit to the plugins
     * that subscribe to `on_revert_history_commit_handlers`.
     *
     * @param { HistoryCommit } commit
     * @param { Object } [params = {}]
     * @param { boolean } [params.ensureNewMutations = false]
     * @param { boolean } [params.restoreFocus = true]
     */
    revertCommit(commit, { ensureNewMutations = false, restoreFocus = true } = {}) {
        this.trigger("on_revert_history_commit_handlers", commit, {
            ensureNewMutations,
            restoreFocus,
        });
    }

    // ============================
    // Reversal (undo/redo) helpers
    // ============================

    /**
     * Undo or redo the last batch of commits that can be undone or redone.
     *
     * @template { Extract<HistoryCommitType, "undo" | "redo"> } T
     * @param {T} type
     */
    reverse(type) {
        this.discardStagedChanges();
        const commitsToReverse = this.getNextCommitsToReverse(type);
        if (!commitsToReverse.length) {
            return;
        }
        /** @type { type extends "undo" ? HistoryCommit<"standard" | "redo"> : HistoryCommit<"undo"> } */
        let reversedCommit;
        for (reversedCommit of commitsToReverse) {
            this.revertCommit(reversedCommit, { ensureNewMutations: true });
            this.revertedCommits.add(reversedCommit.id);
            const { data, metadata } = this.processCommit({
                batchable: reversedCommit.metadata.batchable,
                commit_timestamp: reversedCommit.metadata.commit_timestamp,
                related_commit_id: reversedCommit.id,
            });
            this.appendCommit(new HistoryCommit({ type, data, metadata }));
        }
        this.trigger(
            type === HISTORY_COMMIT_TYPES.UNDO
                ? "on_history_commit_undone_handlers"
                : "on_history_commit_redone_handlers",
            reversedCommit
        );
    }

    /**
     * Return the index in the history of the next commit to undo or redo, or -1
     * if none could be found.
     *
     * @param {Extract<HistoryCommitType, "undo" | "redo">} type
     * @param { number } [fromIndex = this.commits.length] commit index from which to search
     * @returns { number }
     */
    getNextCommitToReverseIndex(type, fromIndex = this.commits.length) {
        // Do not undo/redo the initial commit.
        for (let index = fromIndex - 1; index > 0; index--) {
            const commit = this.commits[index];
            if (this.isCommitReversible(commit) && !this.discardedCommits.has(commit.id)) {
                if (
                    type === HISTORY_COMMIT_TYPES.REDO &&
                    commit.type === HISTORY_COMMIT_TYPES.STANDARD
                ) {
                    return -1;
                } else if (
                    !this.revertedCommits.has(commit.id) &&
                    // Go back to first commit that can be undone.
                    ((type === HISTORY_COMMIT_TYPES.UNDO &&
                        [HISTORY_COMMIT_TYPES.STANDARD, HISTORY_COMMIT_TYPES.REDO].includes(
                            commit.type
                        )) ||
                        // Look for an "undo" commit that has not yet been redone.
                        (type === HISTORY_COMMIT_TYPES.REDO &&
                            commit.type === HISTORY_COMMIT_TYPES.UNDO))
                ) {
                    return index;
                }
            }
        }
        // There are no commits left to be undone/redone, return an index that
        // does not point to any commit
        return -1;
    }

    /**
     * Return the commits to be reverted/redone by a single undo or redo.
     *
     * @template { Extract<HistoryCommitType, "undo" | "redo"> } T
     * @param { T } type
     * @returns { (T extends "undo" ? HistoryCommit<"standard" | "redo"> : HistoryCommit<"undo">)[] }
     */
    getNextCommitsToReverse(type) {
        let referenceCommitIndex = this.getNextCommitToReverseIndex(type);
        // Do not undo/redo the initial commit.
        if (referenceCommitIndex <= 0) {
            return [];
        }
        let nextCommitIndex = this.getNextCommitToReverseIndex(type, referenceCommitIndex);
        const result = [this.commits[referenceCommitIndex]];
        while (
            nextCommitIndex >= 0 &&
            this.canCommitsBeBatched(referenceCommitIndex, nextCommitIndex)
        ) {
            result.push(this.commits[nextCommitIndex]);
            referenceCommitIndex = nextCommitIndex;
            nextCommitIndex = this.getNextCommitToReverseIndex(type, nextCommitIndex);
        }
        return result;
    }

    /**
     * Return true if there is at least one commit in history that can be
     * undone, false otherwise.
     *
     * @returns { boolean }
     */
    canUndo() {
        return this.getNextCommitToReverseIndex(HISTORY_COMMIT_TYPES.UNDO) > 0;
    }

    /**
     * Return true if there is at least one commit in history that can be
     * redone, false otherwise.
     *
     * @returns { boolean }
     */
    canRedo() {
        return this.getNextCommitToReverseIndex(HISTORY_COMMIT_TYPES.REDO) > 0;
    }

    /**
     * Return true if commits can be batched in a single revision (undo/redo),
     * false otherwise.
     * Currrently: commits with a single mutation on the same text node.
     *
     * @param { number } index1
     * @param { number } index2
     * @returns { boolean }
     */
    canCommitsBeBatched(index1, index2) {
        const commit1 = this.commits[index1];
        const commit2 = this.commits[index2];
        if (!commit1.metadata.batchable || !commit2.metadata.batchable) {
            return false;
        }
        // Keep only if close enough in time.
        if (
            Math.abs(commit1.metadata.commit_timestamp - commit2.metadata.commit_timestamp) >
            COMMIT_DEBOUNCE_DELAY
        ) {
            return false;
        }
        return true;
    }

    // ===========================
    // Collaboration compatibility
    // ===========================

    /**
     * Insert a commit at the given index in the history.
     *
     * @param { HistoryCommit } newCommit
     * @param { number } index
     */
    insertRemoteCommit(newCommit, index) {
        this.trigger("on_will_rebase_history_handlers");
        // The last commit is an uncommited draft, revert it first.
        this.stash();
        const commitsAfterNewCommit = this.commits.slice(index);
        for (const commitToRevert of commitsAfterNewCommit.slice().reverse()) {
            this.revertCommit(commitToRevert);
        }
        this.applyCommit(newCommit);
        this.trigger("on_remote_history_commit_applied_handlers", newCommit);
        this.commits.splice(index, 0, newCommit);
        for (const commitToApply of commitsAfterNewCommit) {
            this.applyCommit(commitToApply);
        }
        // Reapply the uncommitted draft, since this is not an operation that
        // should cancel it.
        this.unstash();
        this.trigger("on_history_rebased_handlers");
    }

    /**
     * Give a chance to other plugins to prevent the reversal of the given
     * commit. Return true if it's reversible, false otherwise.
     *
     * @param { HistoryCommit } commit
     * @returns { boolean }
     */
    isCommitReversible(commit) {
        return this.checkPredicates("is_history_commit_reversible_predicates", commit) ?? true;
    }

    // =======
    // Preview
    // =======

    /**
     * Returns a function that can be later called to revert history to the
     * current state.
     *
     * @returns { Function }
     */
    makeSavePoint() {
        const savePoint = new HistoryCommit({
            type: HISTORY_COMMIT_TYPES.SAVEPOINT,
            data: this.processThrough("save_point_history_commit_data_processors", {}),
            metadata: this.processThrough("save_point_history_commit_metadata_processors", {
                related_commit_id: this.commits.at(-1).id,
                has_been_restored: false,
            }),
        });
        // Processors can stage pending changes: collect the draft after them.
        this.collectStagedProperties(savePoint.data, savePoint.metadata);
        return () => {
            if (savePoint.metadata.has_been_restored) {
                return;
            }
            this.discardStagedChanges();
            const { related_commit_id: relatedCommitId } = savePoint.metadata;
            const isLastCommit = relatedCommitId === this.commits.at(-1).id;
            const index = this.commits.findLastIndex((commit) => commit?.id === relatedCommitId);
            const commitsToRestore = this.commits.slice(index === -1 ? 1 : index + 1).reverse();
            /** @type { HistoryCommit[] } */
            const irreversibleCommits = [];
            for (const commitToRestore of commitsToRestore) {
                const isReversible = this.isCommitReversible(commitToRestore);
                // Savepoint restoration is used for previews, so keep focus on the
                // external UI (for example the color picker) while reverting the
                // underlying history commit.
                this.revertCommit(commitToRestore, {
                    ensureNewMutations: true,
                    restoreFocus: false,
                });
                this.trigger("on_history_commit_restored_handlers");
                if (isReversible) {
                    this.discardedCommits.add(commitToRestore.id);
                } else {
                    irreversibleCommits.unshift(commitToRestore);
                }
            }
            // Re-apply every non reversible commit (typically collaborators commits).
            for (const irreversibleCommit of irreversibleCommits) {
                this.applyCommit(irreversibleCommit, {
                    ensureNewMutations: true,
                    restoreSelection: true,
                });
                this.trigger("on_irreversible_history_commit_applied_handlers");
            }
            if (!isLastCommit) {
                // Register resulting mutations as a new "restore" commit
                // (prevent undo).
                /** @type { HistoryCommit<"restore"> } */
                const restoreCommit = new HistoryCommit({
                    type: HISTORY_COMMIT_TYPES.RESTORE,
                    ...this.processCommit({
                        related_commit_id: relatedCommitId,
                        reverted_commit_ids: commitsToRestore.map(({ id }) => id),
                        reapplied_commit_ids: irreversibleCommits.map(({ id }) => id),
                    }),
                });
                this.appendCommit(restoreCommit);
            }
            savePoint.metadata.has_been_restored = true;
            this.trigger("on_savepoint_restored_handlers", savePoint);
        };
    }

    /**
     * Return a object containing functions meant to preview, apply, and revert
     * an operation.
     *
     * @param { Function } operation
     * @returns { PreviewableOperation }
     */
    makePreviewableOperation(operation) {
        let revertOperation = () => {};

        return {
            preview: (...args) => {
                revertOperation();
                revertOperation = this.makeSavePoint();
                this.isPreviewing = true;
                this.trigger("on_will_preview_handlers");
                operation(...args);
                // todo: We should not add a commit on preview as it would send
                // unnecessary commits in collaboration and let the other peer
                // see what we preview.
                //
                // The operation should be similar to the 'commit' (normalize
                // etc...) hence the call to 'commit' (but we need to remove it
                // for the collaboration).
                this.commit();
            },
            commit: (...args) => {
                revertOperation();
                this.isPreviewing = false;
                operation(...args);
                this.commit();
            },
            revert: () => {
                revertOperation();
                revertOperation = () => {};
                this.isPreviewing = false;
            },
        };
    }

    /**
     * Return a object containing functions meant to preview, apply, and revert
     * an asynchronous operation.
     *
     * @param { Function } operation
     * @returns { PreviewableOperation }
     */
    makePreviewableAsyncOperation(operation) {
        let revertOperation = async () => {};

        return {
            preview: async (...args) => {
                await revertOperation();
                const { promise, resolve } = Promise.withResolvers();
                const revertSavePoint = this.makeSavePoint();
                revertOperation = async () => {
                    await promise;
                    revertSavePoint();
                };
                this.isPreviewing = true;
                try {
                    this.trigger("on_will_preview_handlers");
                    await operation(...args);
                } catch (error) {
                    revertSavePoint();
                    throw error;
                } finally {
                    resolve();
                }
                if (this.isDestroyed) {
                    return;
                }
                // todo: We should not add a commit on preview as it would send
                // unnecessary commits in collaboration and let the other peer
                // see what we preview.
                //
                // The operation should be similar to the 'commit' (normalize
                // etc...) hence the call to 'commit' (but we need to remove it
                // for the collaboration).
                this.commit();
            },
            commit: async (...args) => {
                await revertOperation();
                this.isPreviewing = false;
                const revertSavePoint = this.makeSavePoint();
                try {
                    await operation(...args);
                } catch (error) {
                    revertSavePoint();
                    throw error;
                }
                if (this.isDestroyed) {
                    return;
                }
                this.commit();
            },
            revert: async () => {
                if (this.isDestroyed) {
                    return;
                }
                await revertOperation();
                revertOperation = () => {};
                this.isPreviewing = false;
            },
        };
    }

    /**
     * Return true if a preview is in progress, false otherwise.
     *
     * @returns { boolean }
     */
    getIsPreviewing() {
        return !!this.isPreviewing;
    }

    // =============
    // DOM Listeners
    // =============

    /**
     * @param { InputEvent } ev
     */
    onDocumentBeforeInput(ev) {
        if (this.editable.contains(ev.target)) {
            return;
        }
        if (["historyUndo", "historyRedo"].includes(ev.inputType)) {
            this._onKeyupResetContenteditableNodes.push(
                ...this.editable.querySelectorAll("[contenteditable=true]")
            );
            if (this.editable.getAttribute("contenteditable") === "true") {
                this._onKeyupResetContenteditableNodes.push(this.editable);
            }

            for (const node of this._onKeyupResetContenteditableNodes) {
                node.setAttribute("contenteditable", false);
            }
        }
    }

    /**
     * @param { InputEvent } ev
     */
    onDocumentInput(ev) {
        if (
            ["historyUndo", "historyRedo"].includes(ev.inputType) &&
            this._onKeyupResetContenteditableNodes.length
        ) {
            for (const node of this._onKeyupResetContenteditableNodes) {
                node.setAttribute("contenteditable", true);
            }
            this._onKeyupResetContenteditableNodes = [];
        }
    }
}

/**
 * @typedef { string } HistoryCommitId
 * @typedef { typeof HISTORY_COMMIT_TYPES[keyof typeof HISTORY_COMMIT_TYPES] } HistoryCommitType
 * @typedef { Exclude<HistoryCommitType, "savePoint" | "stash"> } WritableHistoryCommitType
 */
/**
 * The changes of a commit: the data of its data properties, and its DOM
 * mutations, which are not a data property yet.
 *
 * @template { HistoryCommitType } [T=WritableHistoryCommitType]
 * @typedef { { [Id in HistoryDataPropertyId]?: HistoryData<Id>[] } & Record<string, any> } HistoryCommitData<T>
 */
/**
 * The description of a commit: the values of its metadata properties, and the
 * history's own metadata. A savepoint can also hold metadata that plugins need
 * to restore it.
 *
 * @template { HistoryCommitType } [T=WritableHistoryCommitType]
 * @typedef { {
 *   [Id in HistoryMetadataPropertyId]?: import("plugins").HistoryMetadataProperties[Id]
 * } & {
 *   author_timestamp?: number,
 *   commit_timestamp?: number,
 *   previous_commit_id?: HistoryCommitId,
 * } & (
 *   T extends "savePoint" | "restore" | "stash"
 *     ? {}
 *     : { batchable: boolean }
 * ) & (
 *   T extends "standard" | "stash" | "savePoint"
 *     ? {}
 *     : { related_commit_id: HistoryCommitId }
 * ) & (
 *   T extends "restore"
 *     ? {
 *         reverted_commit_ids: HistoryCommitId[],
 *         reapplied_commit_ids: HistoryCommitId[],
 *       }
 *     : {}
 * ) & (
 *   T extends "savePoint"
 *     ? {
 *         related_commit_id: HistoryCommitId,
 *         has_been_restored: boolean,
 *       } & Record<string, any>
 *     : {}
 * ) } HistoryCommitMetadata<T>
 */

/**
 * @template { HistoryCommitType } [T=WritableHistoryCommitType]
 */
export class HistoryCommit {
    /**
     * @param { Object } [params = {}]
     * @param { HistoryCommitId } [params.id = this.generateId()]
     * @param { T } [params.type = HISTORY_COMMIT_TYPES.STANDARD]
     * @param { HistoryCommitData<T> } [params.data = {}]
     * @param { HistoryCommitMetadata<T> } [params.metadata = {}]
     */
    constructor({
        id = this.generateId(),
        type = HISTORY_COMMIT_TYPES.STANDARD,
        data = {},
        metadata = {},
    } = {}) {
        /** @type { HistoryCommitId } */
        this.id = id;
        /** @type { T } */
        this.type = type;
        /** @type { HistoryCommitData<T> } */
        this.data = data;
        /** @type { HistoryCommitMetadata<T> } */
        this.metadata = metadata;
    }

    /**
     * @returns { HistoryCommitId }
     */
    generateId() {
        // No need for secure random number.
        return Math.floor(Math.random() * Math.pow(2, 52)).toString();
    }
}
