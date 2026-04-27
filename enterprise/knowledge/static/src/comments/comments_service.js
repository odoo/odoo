import { registry } from "@web/core/registry";
import { batched, reactive } from "@odoo/owl";
import { Deferred } from "@web/core/utils/concurrency";
import { rpc } from "@web/core/network/rpc";
import { browser } from "@web/core/browser/browser";
import { uuid } from "@web/views/utils";
import { effect } from "@web/core/utils/reactive";

const ARTICLE_THREAD_FIELDS = [
    "id",
    "article_id",
    "article_anchor_text",
    "is_resolved",
    "write_date",
];

export const LOAD_THREADS_LIMIT = 30;

function clearThreadComposer(composer) {
    if (!composer) {
        return;
    }
    composer.clear();
    browser.localStorage.removeItem(composer.localId);
}

export const knowledgeCommentsService = {
    dependencies: ["orm", "mail.store"],
    start(env, services) {
        this.services = services;
        this.commentsState = reactive({
            articleId: undefined,
            activeThreadId: undefined,
            // database records
            threadRecords: {},
            // mail.store instances
            threads: {},
            disabledEditorThreads: {},
            // editor metadata
            editorThreads: {},
            displayMode: "handler", // 'handler' 'panel'
            focusedThreads: new Set(),
            deletedThreadIds: new Set(),
            hasFocus(threadId) {
                return this.focusedThreads.has(threadId) || this.activeThreadId === threadId;
            },
        });
        let previousArticleId;
        effect(
            (state) => {
                if (previousArticleId !== state.articleId) {
                    this.resetForArticleId();
                    previousArticleId = state.articleId;
                }
            },
            [this.commentsState]
        );
        return {
            createThread: this.createThread.bind(this),
            createVirtualThread: this.createVirtualThread.bind(this),
            deleteThread: this.deleteThread.bind(this),
            fetchMessages: this.fetchMessages.bind(this),
            getCommentsState: this.getCommentsState.bind(this),
            loadRecords: this.loadRecords.bind(this),
            loadThreads: this.loadThreads.bind(this),
            setArticleId: this.setArticleId.bind(this),
            updateResolveState: this.updateResolveState.bind(this),
        };
    },
    async createThread(value, postData) {
        if (!value || !("undefined" in this.commentsState.editorThreads)) {
            return;
        }
        const loadingId = this.loadingId;
        const record = await rpc("/knowledge/thread/create", {
            article_id: this.commentsState.articleId,
            article_anchor_text: this.commentsState.editorThreads["undefined"].anchorText,
            fields: ARTICLE_THREAD_FIELDS,
        });
        if (loadingId !== this.loadingId) {
            return;
        }
        this.commentsState.threadRecords[record.id] = record;
        this.commentsState.editorThreads[record.id] = this.commentsState.editorThreads["undefined"];
        delete this.commentsState.editorThreads["undefined"];
        this.commentsState.editorThreads[record.id].setThreadId(record.id);
        clearThreadComposer(this.commentsState.threads["undefined"].composer);
        const thread = this.services["mail.store"].Thread.insert({
            id: record.id,
            model: "knowledge.article.thread",
            articleId: this.commentsState.articleId,
        });
        this.commentsState.threads[record.id] = thread;
        thread.post(value, postData);
        return thread;
    },
    createVirtualThread() {
        this.commentsState.threads["undefined"] = this.services["mail.store"].Thread.insert({
            id: undefined,
            model: "knowledge.article.thread",
            articleId: this.commentsState.articleId,
        });
        clearThreadComposer(this.commentsState.threads["undefined"].composer);
        return this.commentsState.threads["undefined"];
    },
    async deleteThread(resId) {
        if (resId === "undefined") {
            return;
        }
        this.batchedDeleteThread.threadIds.add(resId);
        this.batchedDeleteThread();
    },
    // threadId is a number
    async fetchMessages(threadId) {
        const deferred = new Deferred();
        this.batchedFetchMessages.deferredPromises[threadId] ||= [];
        this.batchedFetchMessages.deferredPromises[threadId].push(deferred);
        this.batchedFetchMessages.threadIds.add(threadId);
        this.batchedFetchMessages();
        return await deferred;
    },
    getCommentsState() {
        return this.commentsState;
    },
    loadRecords(articleId, { domain, ignoreBatch, includeLoaded, limit, threadId } = {}) {
        if (this.commentsState.articleId !== articleId) {
            return;
        }
        if (ignoreBatch) {
            return this._loadRecords({
                domain,
                limit,
                includeLoaded,
            });
        }
        if (threadId) {
            if (threadId === "undefined") {
                return;
            }
            this.batchedLoadRecords.threadIds.add(threadId);
            this.batchedLoadRecords();
        }
    },
    loadThreads(resIds) {
        for (const resId of resIds) {
            this.commentsState.threads[resId] = this.services["mail.store"].Thread.insert({
                id: resId === "undefined" ? undefined : resId,
                model: "knowledge.article.thread",
                articleId: this.commentsState.articleId,
            });
        }
    },
    makeBatchedDeleteThread() {
        const deleteThread = async () => {
            if (this.loadingId !== batch.loadingId) {
                return;
            }
            const resIds = [];
            for (const resId of batch.threadIds) {
                resIds.push(parseInt(resId));
            }
            batch.threadIds = new Set();
            try {
                await this.services["orm"].unlink("knowledge.article.thread", resIds);
            } catch {
                // deleted threads may already be deleted, or the current user
                // may not have the right to delete them.
            }
            if (this.loadingId !== batch.loadingId) {
                return;
            }
            for (const resId of resIds) {
                delete this.commentsState.threadRecords[resId];
                delete this.commentsState.threads[resId];
                this.commentsState.deletedThreadIds.add(resId.toString());
                this.commentsState.editorThreads[resId]?.removeBeacons();
            }
        };
        const batch = batched(deleteThread);
        batch.threadIds = new Set();
        batch.loadingId = this.loadingId;
        return batch;
    },
    makeBatchedFetchMessages() {
        const fetchMessages = async () => {
            if (this.loadingId !== batch.loadingId) {
                return;
            }
            const deferredPromises = batch.deferredPromises;
            const thread_ids = Array.from(batch.threadIds);
            batch.threadIds = new Set();
            batch.deferredPromises = {};
            let error;
            let result;
            try {
                result = await rpc("/knowledge/threads/messages", {
                    thread_model: "knowledge.article.thread",
                    thread_ids,
                });
            } catch (e) {
                error = e;
            }
            // thread_id is a number, not a string (used for backend)
            for (const thread_id in deferredPromises) {
                for (const deferred of deferredPromises[thread_id]) {
                    if (error) {
                        deferred.reject(error);
                    } else {
                        deferred.resolve(result[thread_id]);
                    }
                }
            }
        };
        const batch = batched(fetchMessages);
        batch.deferredPromises = {};
        batch.threadIds = new Set();
        batch.loadingId = this.loadingId;
        return batch;
    },
    makeBatchedLoadRecords() {
        const loadRecords = async () => {
            if (this.loadingId !== batch.loadingId) {
                return;
            }
            const excludedSet = new Set(Object.keys(this.commentsState.threadRecords));
            const targetedSet = batch.threadIds;
            batch.threadIds = new Set();
            for (const threadId of [...targetedSet]) {
                if (excludedSet.has(threadId)) {
                    targetedSet.delete(threadId);
                }
            }
            let threadRecords = [];
            if (targetedSet.size) {
                const queryDomain = [
                    ["article_id", "=", this.commentsState.articleId],
                    ["id", "in", [...targetedSet]],
                ];
                threadRecords = await this.services["orm"].searchRead(
                    "knowledge.article.thread",
                    queryDomain,
                    ARTICLE_THREAD_FIELDS
                );
                if (this.loadingId !== batch.loadingId) {
                    return;
                }
                for (const threadRecord of threadRecords) {
                    const threadId = threadRecord.id.toString();
                    this.commentsState.threadRecords[threadId] = threadRecord;
                    if (threadRecord.is_resolved) {
                        this.commentsState.editorThreads[threadId]?.disableBeacons();
                    } else {
                        this.commentsState.disabledEditorThreads[threadId]?.enableBeacons();
                    }
                }
            }
            if (targetedSet.size) {
                // cleanup targetedThreadIds which do not exist anymore
                for (const threadId of targetedSet) {
                    if (
                        !(threadId in this.commentsState.threadRecords) &&
                        !this.commentsState.editorThreads[threadId]?.isProtected()
                    ) {
                        this.batchedDeleteThread.threadIds.add(threadId);
                    }
                }
                if (this.batchedDeleteThread.threadIds.size) {
                    this.batchedDeleteThread();
                }
            }
        };
        const batch = batched(loadRecords);
        batch.loadingId = this.loadingId;
        batch.threadIds = new Set();
        return batch;
    },
    makeLoadRecords() {
        const loadRecords = async ({ domain, limit, includeLoaded } = {}) => {
            if (!limit) {
                limit = LOAD_THREADS_LIMIT;
            }
            const options = {
                limit,
            };
            const queryDomain = [["article_id", "=", this.commentsState.articleId]];
            if (domain) {
                queryDomain.push(...domain);
            }
            if (!includeLoaded) {
                const excludedThreadIds = Object.keys(this.commentsState.threadRecords);
                queryDomain.push(["id", "not in", excludedThreadIds]);
            }
            const threadRecords = await this.services["orm"].searchRead(
                "knowledge.article.thread",
                queryDomain,
                ARTICLE_THREAD_FIELDS,
                options
            );
            if (this.loadingId !== loadRecords.loadingId) {
                return;
            }
            for (const threadRecord of threadRecords) {
                const threadId = threadRecord.id.toString();
                this.commentsState.threadRecords[threadId] = threadRecord;
                if (threadRecord.is_resolved) {
                    this.commentsState.editorThreads[threadId]?.disableBeacons();
                } else {
                    this.commentsState.disabledEditorThreads[threadId]?.enableBeacons();
                }
            }
            return threadRecords.length;
        };
        loadRecords.loadingId = this.loadingId;
        return loadRecords;
    },
    resetForArticleId() {
        this.loadingId = uuid();
        this.commentsState.activeThreadId = undefined;
        this.commentsState.focusedThreads = new Set();
        this.commentsState.threadRecords = {};
        this.commentsState.threads = {};
        this.commentsState.disabledEditorThreads = {};
        this.commentsState.editorThreads = {};
        this.batchedFetchMessages = this.makeBatchedFetchMessages();
        this.batchedDeleteThread = this.makeBatchedDeleteThread();
        this.batchedLoadRecords = this.makeBatchedLoadRecords();
        this._loadRecords = this.makeLoadRecords();
    },
    setArticleId(articleId) {
        if (articleId !== this.commentsState.articleId) {
            this.commentsState.articleId = articleId;
            this.resetForArticleId();
        }
    },
    async updateResolveState(resId, resolvedState) {
        const loadingId = this.loadingId;
        try {
            await this.services["orm"].write("knowledge.article.thread", [parseInt(resId)], {
                is_resolved: resolvedState,
            });
        } catch {
            return false;
        }
        if (this.loadingId !== loadingId) {
            return false;
        }
        this.commentsState.threadRecords[resId].is_resolved = resolvedState;
        if (resolvedState) {
            this.commentsState.editorThreads[resId]?.disableBeacons();
        } else {
            this.commentsState.disabledEditorThreads[resId]?.enableBeacons();
        }
        return true;
    },
};

registry.category("services").add("knowledge.comments", knowledgeCommentsService);
