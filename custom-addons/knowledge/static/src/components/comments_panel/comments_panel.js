/** @odoo-module **/

import { registry } from '@web/core/registry';
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';
import { useBus, useService } from '@web/core/utils/hooks';

import { KnowledgeCommentsThread } from '../comment/comment';

import { Component, onWillStart, useRef, useState } from '@odoo/owl';


export class KnowledgeArticleCommentsPanel extends Component {
    static template = 'knowledge.KnowledgeArticleCommentsPanel';
    static components = { KnowledgeCommentsThread };
    static props = { ...standardWidgetProps };

    setup() {
        this.state = useState({
            displayCommentsPanel: false,
            commentMode: 'unresolved',
            comments: {},
            mounted: false
        });

        this.threadRecords = [];

        this.commentsActive = false;

        this.root = useRef('root');

        this.boundFunctions = {
            destroyComment: (id, anchor, unlink=false) => this.destroyComment(id, anchor, unlink),
            changeCommentResolvedState:
            this._changeCommentResolvedState.bind(this)
        };

        this.threadService = useService('mail.thread');
        this.orm = useService('orm');
        this.userService = useService('user');

        onWillStart(async () => {
            this.state.isInternalUser = await this.userService.hasGroup('base.group_user');
        });

        useBus(this.env.bus, 'KNOWLEDGE:TOGGLE_COMMENTS', this.toggleComments.bind(this));
        useBus(this.env.bus, 'KNOWLEDGE_COMMENTS_PANELS:CHANGE_COMMENT_STATE', this.changeCommentResolvedState.bind(this));
        useBus(this.env.bus, 'KNOWLEDGE_COMMENTS_PANELS:CREATE_COMMENT', this.insertNewThreadFromHandler.bind(this));
        useBus(this.env.bus, 'KNOWLEDGE_COMMENTS_PANEL:SYNCHRONIZE_THREADS', this.loadData.bind(this));
        useBus(this.env.bus, 'KNOWLEDGE_COMMENTS_PANELS:DELETE_COMMENT', ({detail}) => {
            delete this.state.comments[detail.removedCommentId];
            this.threadRecords = this.threadRecords.filter((record) => record.id !== detail.removedCommentId);
        });
    }

    get displayedComments() {
        return Object.values(this.state.comments)
            .sort((threadA, threadB) => threadB.writeDate - threadA.writeDate)
            .filter((thread) => {
                if (this.state.commentMode === 'all') {
                    return true;
                }
                return this.state.commentMode === 'resolved' ? thread.isResolved : !thread.isResolved;
            });
    }

    loadData({detail}) {
        const allCommentsThread = detail.allCommentsThread;
        this.commentsActive = allCommentsThread && allCommentsThread.length !== 0;
        if (allCommentsThread) {
            this.threadRecords = allCommentsThread;
        }
        this.fillThreads();
    }

    sortRecords() {
        this.threadRecords.sort((recordA, recordB) => {
            const dateA = new Date(recordA.write_date);
            const dateB = new Date(recordB.write_date);
            return dateB - dateA;
        });
    }

    fillThreads () {
        this.sortRecords();
        this.state.comments = {};
        this.threadRecords.filter(
            (record) => {
                if (this.state.commentMode === 'all'){
                    return true;
                }
                return this.state.commentMode === 'resolved' ? record.is_resolved : !record.is_resolved;
            }).forEach(
            (record) => {
                const allCommentsAnchors = document.querySelectorAll(`.knowledge-thread-comment[data-id="${record.id}"]`);
                const thread = {
                    thread: this.threadService.getThread('knowledge.article.thread', record.id),
                    knowledgeThreadId: record.id,
                    isResolved: record.is_resolved,
                    anchors: allCommentsAnchors.length ?  Array.from(allCommentsAnchors) : [],
                    articleId: this.props.record.resId
                };
                this.state.comments[record.id] = thread;
            });
    }

    insertNewThreadFromHandler(event) {
        const newlyCreatedComment = Object.assign({}, event.detail.comment, {
            insertNewThread: this.insertNewThread.bind(this),
        });
        this.state.commentMode = 'unresolved';
        if (newlyCreatedComment.isCreationMode) {
            this.state.comments['undefined'] = newlyCreatedComment;
            return;
        }
        if (!this.commentsActive) {
            this.commentsActive = true;
            this.env.bus.trigger('KNOWLEDGE_COMMENTS_PANEL:DISPLAY_BUTTON', {commentsActive: true, displayCommentsPanel: this.state.displayCommentsPanel});
        }
        this.threadRecords.unshift({
            id: newlyCreatedComment.knowledgeThreadId,
            article_id: this.props.record.resId,
            is_resolved: newlyCreatedComment.isResolved,
            write_date: newlyCreatedComment.writeDate
        });
        this.state.comments[newlyCreatedComment.knowledgeThreadId || 'undefined'] = newlyCreatedComment;
    }

    insertNewThread(id, thread) {
        const newCommentThread = Object.assign({}, this.state.comments['undefined'], {knowledgeThreadId: id, thread: thread, isCreationMode: false});
        this.threadRecords.unshift({
            id: newCommentThread.knowledgeThreadId,
            article_id: this.props.record.resId,
            is_resolved: false,
            write_date: luxon.DateTime.now(),
        });
        this.state.comments[id] = newCommentThread;
        this.env.bus.trigger('KNOWLEDGE_COMMENTS_PANEL:CREATE_COMMENT', {newComment: newCommentThread});
        delete this.state.comments['undefined'];
    }

    _onChangeMode(event) {
        const input = event.target;
        this.state.commentMode = input.value;
        this.fillThreads();
    }

    toggleComments(event) {
        this.fillThreads();
        this.root.el?.parentElement?.classList[event.detail.displayCommentsPanel ? 'remove' : 'add']('d-none');
        this.state.commentMode = event.detail.forcedMode || this.state.commentMode;
        this.state.displayCommentsPanel = event.detail.displayCommentsPanel;
        this.env.bus.trigger('KNOWLEDGE_COMMENTS_PANELS:TOGGLE_HANDLER', {displayCommentsHandler: !this.state.displayCommentsPanel});
    }

    changeCommentResolvedState(ev) {
        const { id, newResolvedState } = ev.detail;
        this._changeCommentResolvedState(id, newResolvedState, ev);
    }

    async _changeCommentResolvedState(threadId, newResolvedState, ev=undefined) {
        if (!ev) {
            try{
                this.env.bus.trigger('KNOWLEDGE:CHANGE_COMMENT_STATE', {threadId: threadId, newResolvedState: newResolvedState});
            } catch {
                return false;
            }
        }
        this.threadRecords.find((element) => element.id === threadId)['is_resolved'] = newResolvedState;
        if (this.state.commentMode !== 'all') {
            delete this.state.comments[threadId];
        }
        return true;
    }

    async destroyComment(threadId, _anchor, unlink) {
        let threadToDestroy = this.state.comments[threadId];
        if (!threadToDestroy) {
            if (!this.state.comments['undefined']) {
                return;
            }
            threadToDestroy = this.state.comments['undefined'];
        }
        for (const commentAnchor of threadToDestroy.anchors) {
            const text = document.createTextNode(commentAnchor.textContent);
            commentAnchor.replaceWith(text);
        }
        this.threadRecords = this.threadRecords.filter(record => record.id !== threadId);
        delete this.state.comments[threadId];
        this.sortRecords();
        if (unlink) {
            this.orm.unlink('knowledge.article.thread', [threadId]);
        }
        await this.props.record.save();
    }
}

export const knowledgeCommentsPanel = {
    component: KnowledgeArticleCommentsPanel,
    additionalClasses: ['d-none', 'col-12', 'col-lg-4', 'border-start', 'd-print-none']
};

registry.category('view_widgets').add('knowledge_comments_panel', knowledgeCommentsPanel);
