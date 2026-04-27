import { MIN_THREAD_WIDTH, KnowledgeCommentsThread } from "../comment/comment";
import { useCallbackRecorder } from "@web/search/action_hook";
import { batched, Component, reactive, useEffect, useState, useSubEnv } from "@odoo/owl";
import { CommentBeaconManager } from "../../comments/comment_beacon_manager";
import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { localization } from "@web/core/l10n/localization";

const MAX_THREAD_WIDTH = 400;
const SMALL_THREAD_WIDTH = 40; // o_knowledge_small_ui

export class KnowledgeCommentsHandler extends Component {
    static template = "knowledge.KnowledgeCommentsHandler";
    static components = { KnowledgeCommentsThread };
    static props = {
        commentBeaconManager: { type: CommentBeaconManager },
        contentRef: { type: Object },
    };

    setup() {
        this.commentsService = useService("knowledge.comments");
        this.commentsState = useState(this.commentsService.getCommentsState());
        const debouncedThreadDimensions = debounce(() => {
            this.computeThreadDimensions();
        }, 300);
        const batchedComputeVerticalDimensions = batched(this.computeVerticalDimensions.bind(this));
        useSubEnv({
            threadHeights: reactive({}, batchedComputeVerticalDimensions),
        });
        this.lastActiveThreadId;
        this.state = useState({
            threadDimensions: {
                horizontal: {},
                threadTops: {},
            },
        });
        useCallbackRecorder(this.env.__onLayoutGeometryChange__, debouncedThreadDimensions);
        let activeThreadId;
        useEffect(
            () => {
                if (this.commentsState.activeThreadId !== activeThreadId) {
                    activeThreadId = this.commentsState.activeThreadId;
                    batchedComputeVerticalDimensions();
                }
            },
            () => [this.commentsState.activeThreadId]
        );
        useEffect(
            () => {
                const editorThreads = Object.keys(this.commentsState.editorThreads);
                if (
                    editorThreads.some((threadId) => {
                        return this.props.commentBeaconManager.sortedThreadIds.includes(threadId);
                    })
                ) {
                    debouncedThreadDimensions();
                }
            },
            () => [
                this.commentsState.editorThreads,
                Object.keys(this.commentsState.editorThreads).toString(),
            ]
        );
    }

    get mainPositionThreadId() {
        if (
            this.commentsState.activeThreadId &&
            this.commentsState.activeThreadId !== this.lastActiveThreadId
        ) {
            this.lastActiveThreadId = this.commentsState.activeThreadId;
        } else if (
            !this.props.commentBeaconManager.sortedThreadIds.includes(this.lastActiveThreadId)
        ) {
            this.lastActiveThreadId = undefined;
        }
        return this.lastActiveThreadId || this.props.commentBeaconManager.sortedThreadIds.at(0);
    }

    computeHorizontalDimensions() {
        if (!this.props.contentRef.el) {
            return;
        }
        const rtl = localization.direction === "rtl";
        const keys = {
            paddingRight: "paddingRight",
            left: "left",
            right: "right",
        };
        if (rtl) {
            Object.assign(keys, {
                paddingRight: "paddingLeft",
                left: "right",
                right: "left",
            });
        }
        const contentStyle = getComputedStyle(this.props.contentRef.el);
        const paddingRight = parseInt(contentStyle[keys.paddingRight]) || 0;

        // Manually calculate margin to circumvent zero-margin bug in chromium-based browsers
        const contentRect = this.props.contentRef.el.getBoundingClientRect();
        const parentRect = this.props.contentRef.el.parentElement.getBoundingClientRect();
        const marginRight = Math.abs(parentRect[keys.right] - contentRect[keys.right]);
        const marginLeft = Math.abs(parentRect[keys.left] - contentRect[keys.left]);

        const availableWidth = Math.max(0, Math.floor(marginRight + paddingRight));
        let width = Math.min(MAX_THREAD_WIDTH, Math.max(0, availableWidth - 20));
        if (!width) {
            return;
        }
        if (width < MIN_THREAD_WIDTH) {
            width = SMALL_THREAD_WIDTH;
        }
        const left =
            (rtl ? -1 : 1) *
            Math.ceil(
                marginLeft +
                    contentRect.width -
                    paddingRight +
                    (availableWidth + (rtl ? 1 : -1) * width) / 2
            );
        this.state.threadDimensions.horizontal = { left, width };
    }

    computeVerticalDimensions() {
        const activeId = this.mainPositionThreadId;
        if (!activeId || this.commentsState.editorThreads[activeId]?.top === undefined) {
            return;
        }
        const threadIds = this.props.commentBeaconManager.sortedThreadIds.filter(
            (threadId) =>
                threadId in this.commentsState.editorThreads &&
                this.commentsState.editorThreads[threadId].top !== undefined
        );
        const index = threadIds.indexOf(activeId);
        this.setThreadTop(activeId, this.commentsState.editorThreads[activeId].top);
        let masterTop = this.getThreadTop(activeId);
        for (let i = index - 1; i >= 0; i--) {
            const threadId = threadIds[i];
            const expectedTop = this.commentsState.editorThreads[threadId].top;
            const height = this.env.threadHeights[threadId]?.height || 0;
            if (expectedTop + height < masterTop) {
                masterTop = expectedTop;
            } else {
                masterTop -= height;
            }
            this.setThreadTop(threadId, masterTop);
        }
        masterTop = this.getThreadTop(activeId) + (this.env.threadHeights[activeId]?.height || 0);
        for (let i = index + 1; i < threadIds.length; i++) {
            const threadId = threadIds[i];
            const expectedTop = this.commentsState.editorThreads[threadId].top;
            masterTop = Math.max(masterTop, expectedTop);
            this.setThreadTop(threadId, masterTop);
            masterTop += this.env.threadHeights[threadId]?.height || 0;
        }
    }

    computeThreadDimensions() {
        this.computeHorizontalDimensions();
        this.computeVerticalDimensions();
    }

    setThreadTop(threadId, top) {
        if (!(threadId in this.state.threadDimensions.threadTops)) {
            this.state.threadDimensions.threadTops[threadId] = {
                top: undefined,
            };
        }
        this.state.threadDimensions.threadTops[threadId].top = top;
    }

    getThreadTop(threadId) {
        return this.state.threadDimensions.threadTops[threadId]?.top;
    }
}
