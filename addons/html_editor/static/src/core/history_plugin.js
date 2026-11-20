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
 * that are computed when a commit is created are staged by
 * `on_will_collect_history_draft_handlers`, which are triggered right before the
 * draft is collected. Properties are applied and reverted in resource order.
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
 * redo, and to revert it on undo or when it is discarded. The commits created
 * by the history (undo, redo, restore) hold a copy of the data they replay, so
 * that they can be replayed without the commits they revert or reapply, which
 * collaborators may not have.
 *
 * The replays of a data property with `shouldRecordReplays` are recorded
 * instead: the commits created by the history hold, as their own changes, what
 * replaying its data actually did, along with what plugins changed during the
 * replay, and replay them like any changes (see `replay`).
 *
 * A data property can declare `takeSnapshot`, which returns the data that
 * recreates its current state from an empty one, for snapshot commits.
 *
 * @template { HistoryDataPropertyId } Id
 * @typedef {Object} HistoryDataProperty
 * @property {import("plugins").HistoryDataProperties[Id]} apply
 * @property {(data: HistoryData<Id>) => void} revert
 * @property {boolean} [shouldRecordReplays]
 * @property {() => HistoryData<Id>[]} [takeSnapshot]
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
 * value when a commit that has one is applied or reverted to create a new
 * commit (undo, redo, savepoint restoration).
 *
 * @template { HistoryMetadataPropertyId } Id
 * @typedef {Object} HistoryMetadataProperty
 * @property {(value: import("plugins").HistoryMetadataProperties[Id]) => void} [apply]
 * @property {(value: import("plugins").HistoryMetadataProperties[Id]) => void} [revert]
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
 * @typedef { ((commit: HistoryCommit, options: { restoreSelection: boolean }) => void)[] } on_apply_history_commit_handlers
 * @typedef { ((commit: HistoryCommit) => void)[] } on_committed_to_history_handlers
 * @typedef { ((lastCommitUndone: HistoryCommit<"standard" | "redo"> | undefined) => void)[] } on_history_commit_undone_handlers
 * @typedef { ((lastCommitRedone: HistoryCommit<"undo"> | undefined) => void)[] } on_history_commit_redone_handlers
 * @typedef { (() => void)[] } on_history_rebased_handlers
 * @typedef { (() => void)[] } on_history_replayed_handlers
 * @typedef { (() => void)[] } on_history_reset_handlers
 * @typedef { ((stashedCommit: HistoryCommit<"stash">) => void)[] } on_pending_changes_unstashed_handlers
 * @typedef { ((newCommit: HistoryCommit) => void)[] } on_remote_history_commit_applied_handlers
 * @typedef { ((commit: HistoryCommit, options: { restoreFocus: boolean }) => void)[] } on_revert_history_commit_handlers
 * @typedef { ((savePoint: HistoryCommit<"savePoint">) => void)[] } on_savepoint_restored_handlers
 * @typedef { ((type: HistoryCommitType) => void)[] } on_will_collect_history_draft_handlers
 * @typedef { (() => void)[] } on_will_invalidate_pending_changes_handlers
 * @typedef { (() => void)[] } on_will_preview_handlers
 * @typedef { (() => void)[] } on_will_rebase_history_handlers
 * @typedef { ((options: { isRecorded: boolean }) => void)[] } on_will_replay_history_handlers
 * @typedef { (() => void)[] } on_will_reset_history_handlers
 *
 * @typedef { ((commit: HistoryCommit) => boolean | undefined)[] } has_history_commit_changes_predicates
 * @typedef { ((commit: HistoryCommit) => boolean | undefined)[] } is_history_commit_reversible_predicates
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

        on_savepoint_restored_handlers: withSequence(0, (savePoint) => {
            this.replay(() => {
                for (const [id, { apply }] of this.dataProperties) {
                    if (savePoint.data[id]) {
                        // The discarded data is applied and staged again.
                        this.stage(id, savePoint.data[id]);
                        for (const data of savePoint.data[id]) {
                            apply(data);
                        }
                    }
                }
            });
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
        const { data, metadata } = this.processCommit(HISTORY_COMMIT_TYPES.STANDARD, {
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
            ...this.processCommit(HISTORY_COMMIT_TYPES.STASH),
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
        this.replay(() => {
            for (const [id, { revert }] of this.dataProperties) {
                const stagedData = this.stagedData[id] ?? [];
                delete this.stagedData[id];
                for (const data of stagedData.toReversed()) {
                    revert(data);
                }
            }
        });
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
     * Apply the data properties of the given commit. The data of the properties
     * whose replays are recorded is the commit's own changes, applied as is.
     * The direction in which a commit created by the history replays the copies
     * it holds depends on its type: an undo commit reverts the data of the
     * commit it reverts, and a restore commit reverts and reapplies the commits
     * it holds. The commits created by the history hold copies of that data
     * rather than what replaying it changes, so it is replayed in a replay that
     * isn't recorded.
     *
     * @param {HistoryReplayedCommit} commit
     * @returns {void}
     */
    applyDataProperties(commit) {
        this.applyData(commit.data, { isRecorded: true });
        this.replay(() => {
            switch (commit.type) {
                case HISTORY_COMMIT_TYPES.UNDO:
                    this.revertData(commit.data, { isRecorded: false });
                    break;
                case HISTORY_COMMIT_TYPES.RESTORE:
                    for (const revertedCommit of commit.data.reverted_commits) {
                        this.revertDataProperties(revertedCommit);
                    }
                    for (const reappliedCommit of commit.data.reapplied_commits) {
                        this.applyDataProperties(reappliedCommit);
                    }
                    break;
                default:
                    this.applyData(commit.data, { isRecorded: false });
            }
        });
    }

    /**
     * Revert the data properties of the given commit: the inverse of
     * `applyDataProperties`.
     *
     * @param {HistoryReplayedCommit} commit
     * @returns {void}
     */
    revertDataProperties(commit) {
        this.revertData(commit.data, { isRecorded: true });
        this.replay(() => {
            switch (commit.type) {
                case HISTORY_COMMIT_TYPES.UNDO:
                    this.applyData(commit.data, { isRecorded: false });
                    break;
                case HISTORY_COMMIT_TYPES.RESTORE:
                    for (const reappliedCommit of commit.data.reapplied_commits.toReversed()) {
                        this.revertDataProperties(reappliedCommit);
                    }
                    for (const revertedCommit of commit.data.reverted_commits.toReversed()) {
                        this.applyDataProperties(revertedCommit);
                    }
                    break;
                default:
                    this.revertData(commit.data, { isRecorded: false });
            }
        });
    }

    /**
     * Apply the data of the data properties whose replays are recorded, or of
     * the others, in order.
     *
     * @param {HistoryCommitData} data
     * @param {Object} options
     * @param {boolean} options.isRecorded whether to apply the data of the
     *        properties whose replays are recorded, or of the others
     * @returns {void}
     */
    applyData(data, { isRecorded }) {
        for (const [id, { apply, shouldRecordReplays = false }] of this.dataProperties) {
            if (shouldRecordReplays === isRecorded) {
                for (const item of data[id] ?? []) {
                    apply(item);
                }
            }
        }
    }

    /**
     * Revert the data of the data properties whose replays are recorded, or of
     * the others, last first.
     *
     * @param {HistoryCommitData} data
     * @param {Object} options
     * @param {boolean} options.isRecorded whether to revert the data of the
     *        properties whose replays are recorded, or of the others
     * @returns {void}
     */
    revertData(data, { isRecorded }) {
        for (const [id, { revert, shouldRecordReplays = false }] of this.dataProperties) {
            if (shouldRecordReplays === isRecorded) {
                for (const item of (data[id] ?? []).toReversed()) {
                    revert(item);
                }
            }
        }
    }

    /**
     * Return whether the given commit has data properties, directly or through
     * the commits it holds.
     *
     * @param {HistoryReplayedCommit} commit
     * @returns {boolean}
     */
    hasDataProperties(commit) {
        if ([...this.dataProperties.keys()].some((id) => commit.data[id]?.length)) {
            return true;
        }
        return (
            commit.type === HISTORY_COMMIT_TYPES.RESTORE &&
            [...commit.data.reverted_commits, ...commit.data.reapplied_commits].some(
                (replayedCommit) => this.hasDataProperties(replayedCommit)
            )
        );
    }

    /**
     * Return the data of the given commit that the history replays, for a
     * commit that replays it: the data of its data properties whose replays
     * aren't recorded or, for a restore commit, the commits it holds. That data
     * is immutable: it is shared rather than cloned.
     *
     * @param {HistoryCommit} commit
     * @returns {HistoryCommitData}
     */
    getReplayedData(commit) {
        if (commit.type === HISTORY_COMMIT_TYPES.RESTORE) {
            const { reverted_commits, reapplied_commits } = commit.data;
            return { reverted_commits, reapplied_commits };
        }
        const data = {};
        for (const [id, { shouldRecordReplays }] of this.dataProperties) {
            if (!shouldRecordReplays && commit.data[id]) {
                data[id] = commit.data[id];
            }
        }
        return data;
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
     * Return the data and metadata of a new commit, made of the properties
     * collected from the draft, as well as metadata provided by this plugin.
     *
     * @template { Exclude<HistoryCommitType, "savePoint"> } [T="standard"]
     * @param { T } type The type of the commit.
     * @param { HistoryCommitMetadata<T> } [metadata = {}]
     * @returns { { data: HistoryCommitData<T>, metadata: HistoryCommitMetadata<T> } }
     */
    processCommit(type, metadata = {}) {
        // Set the timestamp of the commit or keep the timestamp of the commit
        // it reverts:
        metadata.commit_timestamp ??= Date.now();
        metadata.author_timestamp ??= this.authorTimestamp;
        metadata.previous_commit_id = this.commits?.at(-1)?.id;
        const data = {};
        this.collectStagedProperties(type, data, metadata);
        return { data, metadata };
    }

    /**
     * Let plugins stage the values they compute when the draft is collected,
     * then add the values of the properties staged in the draft to the given
     * data and metadata.
     *
     * @param { HistoryCommitType } type The type of the commit or savepoint.
     * @param { HistoryCommitData } data
     * @param { HistoryCommitMetadata } metadata
     * @returns { void }
     */
    collectStagedProperties(type, data, metadata) {
        this.trigger("on_will_collect_history_draft_handlers", type);
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
     * Create and return a "snapshot" commit, which recreates the current state
     * from an empty one with the snapshots of the data properties.
     *
     * @returns { HistoryCommit<"standard"> }
     */
    createSnapshotCommit() {
        /** @type { HistoryCommitData<"standard"> } */
        const data = {};
        for (const [id, { takeSnapshot }] of this.dataProperties) {
            if (takeSnapshot) {
                data[id] = takeSnapshot();
            }
        }
        /** @type { HistoryCommitMetadata<"standard"> } */
        const metadata = { author_timestamp: this.authorTimestamp };
        return new HistoryCommit({ id: this.commits?.at(-1)?.id, data, metadata });
    }

    // ===========================
    // Commit application/reversal
    // ===========================

    /**
     * Replay changes that the history already holds (applying, reverting or
     * discarding them), notifying plugins before and after, so that they don't
     * record them again. A recorded replay creates a commit, which holds what
     * the replay changes: plugins stage it as changes of that commit, except in
     * the replays nested in it that aren't recorded.
     *
     * @param { () => void } operation
     * @param { Object } [options]
     * @param { boolean } [options.isRecorded = false] whether the replay creates
     *        a commit, which holds what it changes
     * @returns { void }
     */
    replay(operation, { isRecorded = false } = {}) {
        this.trigger("on_will_replay_history_handlers", { isRecorded });
        try {
            operation();
        } finally {
            this.trigger("on_history_replayed_handlers");
        }
    }

    /**
     * Apply the data of the given commit, then let the plugins that subscribe
     * to `on_apply_history_commit_handlers` react to it.
     *
     * @param { HistoryCommit } commit
     * @param { Object } [params = {}]
     * @param { boolean } [params.ensureNewMutations = false] whether the replay
     *        creates a commit, which records it
     * @param { boolean } [params.restoreSelection = false]
     */
    applyCommit(commit, { ensureNewMutations = false, restoreSelection = false } = {}) {
        this.replay(
            () => {
                this.applyDataProperties(commit);
                this.trigger("on_apply_history_commit_handlers", commit, { restoreSelection });
            },
            { isRecorded: ensureNewMutations }
        );
    }

    /**
     * Revert the data of the given commit, then let the plugins that subscribe
     * to `on_revert_history_commit_handlers` react to it.
     *
     * @param { HistoryCommit } commit
     * @param { Object } [params = {}]
     * @param { boolean } [params.ensureNewMutations = false] whether the replay
     *        creates a commit, which records it
     * @param { boolean } [params.restoreFocus = true]
     */
    revertCommit(commit, { ensureNewMutations = false, restoreFocus = true } = {}) {
        this.replay(
            () => {
                this.revertDataProperties(commit);
                this.trigger("on_revert_history_commit_handlers", commit, { restoreFocus });
            },
            { isRecorded: ensureNewMutations }
        );
    }

    /**
     * Call the `apply` hooks of the metadata properties with the values of the
     * given commit, which is applied to create a new commit.
     *
     * @param { HistoryCommit } commit
     * @returns { void }
     */
    applyMetadataProperties(commit) {
        for (const [id, { apply }] of this.metadataProperties) {
            if (id in commit.metadata) {
                apply?.(commit.metadata[id]);
            }
        }
    }

    /**
     * Call the `revert` hooks of the metadata properties with the values of the
     * given commit, which is reverted to create a new commit.
     *
     * @param { HistoryCommit } commit
     * @returns { void }
     */
    revertMetadataProperties(commit) {
        for (const [id, { revert }] of this.metadataProperties) {
            if (id in commit.metadata) {
                revert?.(commit.metadata[id]);
            }
        }
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
            this.revertMetadataProperties(reversedCommit);
            this.revertedCommits.add(reversedCommit.id);
            const { data, metadata } = this.processCommit(type, {
                batchable: reversedCommit.metadata.batchable,
                commit_timestamp: reversedCommit.metadata.commit_timestamp,
                related_commit_id: reversedCommit.id,
            });
            Object.assign(data, this.getReplayedData(reversedCommit));
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
            data: {},
            metadata: { related_commit_id: this.commits.at(-1).id, has_been_restored: false },
        });
        this.collectStagedProperties(
            HISTORY_COMMIT_TYPES.SAVEPOINT,
            savePoint.data,
            savePoint.metadata
        );
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
                this.revertMetadataProperties(commitToRestore);
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
                this.applyMetadataProperties(irreversibleCommit);
            }
            if (!isLastCommit) {
                // Register the restoration as a new "restore" commit (prevent
                // undo).
                const { data, metadata } = this.processCommit(HISTORY_COMMIT_TYPES.RESTORE, {
                    related_commit_id: relatedCommitId,
                });
                const toReplayedCommit = (commit) => ({
                    type: commit.type,
                    data: this.getReplayedData(commit),
                });
                data.reverted_commits = commitsToRestore.map(toReplayedCommit);
                data.reapplied_commits = irreversibleCommits.map(toReplayedCommit);
                /** @type { HistoryCommit<"restore"> } */
                const restoreCommit = new HistoryCommit({
                    type: HISTORY_COMMIT_TYPES.RESTORE,
                    data,
                    metadata,
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
 * The changes of a commit: the data of its data properties. A commit created
 * by the history holds the data it replays: an undo or redo commit, the data
 * of the commit it reverts; a restore commit, the commits it reverts and
 * reapplies.
 *
 * @template { HistoryCommitType } [T=WritableHistoryCommitType]
 * @typedef { { [Id in HistoryDataPropertyId]?: HistoryData<Id>[] } & (
 *   T extends "restore"
 *     ? {
 *         reverted_commits: HistoryReplayedCommit[],
 *         reapplied_commits: HistoryReplayedCommit[],
 *       }
 *     : {}
 * ) } HistoryCommitData<T>
 */
/**
 * A commit as a restore commit holds it: its type, and the data the history
 * replays.
 *
 * @typedef { { type: HistoryCommitType, data: HistoryCommitData } } HistoryReplayedCommit
 */
/**
 * The description of a commit: the values of its metadata properties, and the
 * history's own metadata.
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
 *   T extends "savePoint"
 *     ? {
 *         related_commit_id: HistoryCommitId,
 *         has_been_restored: boolean,
 *       }
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
