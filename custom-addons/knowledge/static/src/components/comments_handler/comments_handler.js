/** @odoo-module **/

import { registry } from '@web/core/registry';
import { standardWidgetProps } from '@web/views/widgets/standard_widget_props';
import { KeepLast } from "@web/core/utils/concurrency";
import { useBus, useService } from '@web/core/utils/hooks';
import { useRecordObserver } from '@web/model/relational_model/utils';
import { isZWS } from '@web_editor/js/editor/odoo-editor/src/utils/utils';
import { KnowledgeCommentsThread } from '../comment/comment';

import {
    Component,
    useState,
    onMounted,
    onPatched,
    onWillStart,
    status,
    useEffect,
    useRef,
} from '@odoo/owl';


export class KnowledgeCommentsHandler extends Component {
    static template = 'knowledge.KnowledgeCommentsHandler';
    static components = { KnowledgeCommentsThread };
    static props = { ...standardWidgetProps };

    setup() {
        this.state = useState({
            comments: {},
            creatingThread: false,
            displayCommentsHandler: true,
            newlyCreatedComment: false,
        });
        useBus(this.env.bus, 'KNOWLEDGE:CREATE_COMMENT_THREAD', this.createCommentThread.bind(this));

        useBus(this.env.bus, 'KNOWLEDGE:CHANGE_COMMENT_STATE', this.changeCommentResolvedState.bind(this));
        useBus(this.env.bus, 'KNOWLEDGE_COMMENTS_PANELS:TOGGLE_HANDLER', this.toggleHandler.bind(this));
        useBus(this.env.bus, 'KNOWLEDGE_COMMENTS:CHANGES_DETECTED', this.handleChanges.bind(this));
        useBus(this.env.bus, 'KNOWLEDGE_COMMENTS_PANEL:CREATE_COMMENT', ({detail}) => {
            const newComment = detail.newComment;
            this.state.comments[newComment.knowledgeThreadId] = Object.assign({}, newComment);
            this.allCommentsThreadRecords.push({
                id: newComment.knowledgeThreadId,
                article_id: [newComment.articleId, this.props.record.data.name],
                is_resolved: newComment.isResolved,  write_date: luxon.DateTime.now()
            });
            delete this.state.comments['undefined'];
            this.env.bus.trigger('KNOWLEDGE_WYSIWYG:HISTORY_STEP');
        });
        this.root = useRef('root');

        this.boundFunctions = {
            destroyComment: (id) => this.destroyComment(id),
            changeCommentResolvedState: this._changeCommentResolvedState.bind(this)
        };

        this.threadService = useService('mail.thread');
        this.userService = useService('user');
        this.orm = useService('orm');
        this.rpc = useService('rpc');
        this.searchingArticleThread = new KeepLast();
        this.currentArticleThreadSearch = Promise.resolve();

        let previousArticleId;
        useRecordObserver(async (record) => {
            if (!previousArticleId || record.resId !== previousArticleId) {
                previousArticleId = record.resId;
                this.allCommentsThreadRecords = [];
                this.currentArticleThreadSearch = this.searchingArticleThread.add(
                    this.orm.searchRead(
                        "knowledge.article.thread",
                        [["article_id", "=", record.resId]],
                        ["id", "article_id", "is_resolved", "write_date"]
                    )
                );
                this.allCommentsThreadRecords = await this.currentArticleThreadSearch;
                this.env.bus.trigger("KNOWLEDGE_COMMENTS_PANEL:SYNCHRONIZE_THREADS", {
                    allCommentsThread: this.allCommentsThreadRecords,
                });
                this.env.bus.trigger("KNOWLEDGE_COMMENTS_PANEL:DISPLAY_BUTTON", {
                    commentsActive:
                        this.allCommentsThreadRecords && this.allCommentsThreadRecords.length !== 0,
                    displayCommentsPanel: !this.state.displayCommentsHandler,
                });
            }
        });

        onWillStart(async () => {
            this.state.isInternalUser = await this.userService.hasGroup('base.group_user');
            this.state.isPortalUser = await this.userService.hasGroup('base.group_portal');
        });

        onMounted(() => {
            this.env.bus.trigger('KNOWLEDGE_COMMENTS_PANEL:SYNCHRONIZE_THREADS', {allCommentsThread : this.allCommentsThreadRecords});
            this.triggerButton();
        });

        onPatched(() => {
            if (this.env.services.action.currentController?.action.context.show_resolved_threads) {
                this.env.bus.trigger('KNOWLEDGE:TOGGLE_COMMENTS', {forcedMode: 'resolved', displayCommentsPanel: true});
                this.env.bus.trigger('KNOWLEDGE_COMMENTS_PANEL:DISPLAY_BUTTON', {
                    commentsActive: this.allCommentsThreadRecords && this.allCommentsThreadRecords.length !== 0,
                    displayCommentsPanel: true
                });
                this.env.bus.trigger('KNOWLEDGE_COMMENTS_PANEL:SYNCHRONIZE_THREADS', {allCommentsThread : this.allCommentsThreadRecords});
                this.env.services.action.currentController.action.context.show_resolved_threads = false;
            }
        });

        useEffect(() => {
            this.filterComments().then(() => {
                this.allComments = document.querySelectorAll(
                    ".knowledge-thread-highlighted-comment"
                );
            });
            // add listeners for commented text
            const editable = document.querySelector(
                '.o_field_html .note-editable,.o_field_knowledge_article_html_field .note-editable,.o_field_knowledge_article_html_field .o_readonly'
            );
            if (editable) {
                this.addHoverListeners(editable.parentElement);
            }
            return () => {
                const editable = document.querySelector(
                    '.o_field_html .note-editable,.o_field_knowledge_article_html_field .note-editable,.o_field_knowledge_article_html_field .o_readonly'
                );
                if (editable) {
                    this.removeHoverListeners(editable.parentElement);
                }
            };
        }, () => [this.props.record.resId]);

        useEffect(() => {
            for (const commentId of Object.keys(this.state.comments)) {
                this.updateExistingCommentAnchors(parseInt(commentId));
            }
        }, () => [this.props.record.data.is_locked, this.props.record.data.user_can_write]);
    }

    get displayedComments() {
        return Object.values(this.state.comments).filter((comment) => comment.anchors.length && !comment.isResolved)
            .sort((commentA, commentB) => {
                const topDiff = commentA.top - commentB.top;
                if (!topDiff) {
                    return commentA.anchors[0].getBoundingClientRect().left - commentB.anchors[0].getBoundingClientRect().left;
                }
                return topDiff;
            });
    }

    async triggerButton() {
        await this.env.topbarMountedPromise;
        this.env.bus.trigger('KNOWLEDGE_COMMENTS_PANEL:DISPLAY_BUTTON', {
            commentsActive: this.allCommentsThreadRecords && this.allCommentsThreadRecords.length !== 0,
            displayCommentsPanel: !this.state.displayCommentsHandler
        });
    }

    /**============================================
     *               Listeners
     *=============================================**/

    addHoverListeners(editable) {
        if (editable) {
            editable.addEventListener('mouseover', this.onMouseOver.bind(this));
            editable.addEventListener('focusin', this.showAssignedComment.bind(this));
        }
    }

    removeHoverListeners(editable) {
        if (editable) {
            editable.removeEventListener('mouseover', this.onMouseOver.bind(this));
            editable.removeEventListener('focusin', this.showAssignedComment.bind(this));
        }
    }

    onMouseOver(ev) {
        const commentNode = ev.target.closest('.knowledge-thread-highlighted-comment');
        const relatedNode = ev.relatedTarget?.closest('.knowledge-thread-highlighted-comment');
        if (relatedNode && relatedNode.dataset.id) {
            const id = parseInt(relatedNode.dataset.id);
            if (!this.commentingId && ((commentNode && id !== parseInt(commentNode.dataset.id)) || !commentNode)) {
                document.querySelectorAll(`.knowledge-thread-comment.knowledge-thread-highlighted-comment[data-id='${id}'], .o_knowledge_comment_box[data-id='${id}']`).forEach((node) => {
                    node.classList.remove('focused-comment');
                });
            }
        }
        if (commentNode && commentNode.dataset.id && !commentNode.classList.contains('focused-comment')) {
            const id = parseInt(commentNode.dataset.id);
            document.querySelectorAll(`.knowledge-thread-comment.knowledge-thread-highlighted-comment[data-id='${id}'], .o_knowledge_comment_box[data-id='${id}']`).forEach((node) => {
                node.classList.add('focused-comment');
            });
            if (!this.state.displayCommentsHandler) {
                return;
            }
        }
    }

    showAssignedComment(ev) {
        const commentNode = ev.target.closest('.knowledge-thread-highlighted-comment');
        if (commentNode && commentNode.dataset.id) {
            const commentingId = parseInt(commentNode.dataset.id);
            this.commentingId = commentingId;
            this.env.bus.trigger(`KNOWLEDGE_COMMENT_${commentingId}:HIGHLIGHT`);
            document.querySelector(`.o_knowledge_comment_box[data-id='${commentingId}']`)?.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest'
            });
        } else if (ev.target?.closest('.o_field_knowledge_article_html_field')) {
            this.commentingId = false;
        }
    }

    async toggleHandler(ev) {
        this.state.displayCommentsHandler = ev.detail.displayCommentsHandler;
        if (this.state.displayCommentsHandler) {
            await this.filterComments();
            delete this.state.comments['undefined'];
        }
    }

    /**============================================
     *        Creation + updates of threads
     *=============================================**/

    async createCommentThread(event) {
        const selectedNodes = event.detail.selectedNodes;
        if (!selectedNodes) {
            return;
        }
        const commentAnchors = selectedNodes.map((selectedNode) => {
            const commentThreadAnchor = document.createElement('span');
            commentThreadAnchor.classList.add('knowledge-thread-highlighted-comment', 'knowledge-thread-comment');
            commentThreadAnchor.setAttribute('tabindex', '-1');
            commentThreadAnchor.dataset.id = 'undefined';
            const range = document.createRange();
            range.setStartBefore(selectedNode);
            range.setEndAfter(selectedNode);
            range.surroundContents(commentThreadAnchor);
            return commentThreadAnchor;
        });
        if (!commentAnchors || !commentAnchors.length) {
            return;
        }
        const targetTop = commentAnchors[0].getBoundingClientRect().top;
        const rootTop = document.querySelector('.o_knowledge_body').getBoundingClientRect().top;
        const newlyCreatedComment = {
            isCreationMode: true,
            articleId: this.props.record.resId,
            anchors: commentAnchors,
            top: Math.round(Math.abs(targetTop - rootTop)),
            thread: this.threadService.getThread('knowledge.article.thread', undefined),
            isResolved: false,
            insertNewThread: this.insertNewThread.bind(this),
            writeDate: luxon.DateTime.now(),
        };
        if (!this.state.displayCommentsHandler) {
            this.env.bus.trigger('KNOWLEDGE_COMMENTS_PANELS:CREATE_COMMENT', {comment: newlyCreatedComment});
        }
        this.state.comments['undefined'] = newlyCreatedComment;
    }

    /**
     * This function insert a newly created comment inside the comments array to signify
     * that the comment is indeed created by the user. This way we avoid empty threads inside the
     * DB.
     * @param {*} id ID of the created `knowledge.article.thread`.
     * @param {*} thread Thread object from the thread service inside mail.
     */
    async insertNewThread(id, thread) {
        // Ensure that allCommentsThreadRecords is ready to receive a new thread
        await this.currentArticleThreadSearch;
        // TODO-THJO: Create a service to remove the functions to handle comments
        this.state.comments[id] = Object.assign({}, this.state.comments['undefined'], {thread: thread, knowledgeThreadId: id, isCreationMode: false});
        this.allCommentsThreadRecords.push({id: id, article_id: [this.props.record.resId, this.props.record.data.name], is_resolved: false, write_date: luxon.DateTime.now()});
        this.env.bus.trigger('KNOWLEDGE_COMMENTS_PANELS:CREATE_COMMENT', {comment: this.state.comments[id]});
        delete this.state.comments['undefined'];

        //* This is needed because we do not have an automatic save mechanism.
        //* When we create comments without saving, we create a bunch of comments linked to nothing
        //* => leading to a bunch of unnecessary noise.
        //TODO: When we add the autosave => clean all the save from comments
        await this.props.record.save({reload: false});
        this.env.bus.trigger('KNOWLEDGE_WYSIWYG:HISTORY_STEP');
    }

    /**
     * This function filters the comments the comments stored in `this.allCommentsThreadRecords to only get
     * the ones that are represented in the body of the article. Meaning that there is an anchor in the
     * body with the id of a thread.
     */
    async filterComments() {
        this.state.comments = {};
        // ensure that allCommentsThreadRecords is ready before filtering
        // comments
        await this.currentArticleThreadSearch;
        this.allComments = document.querySelectorAll('.knowledge-thread-comment');
        if (this.allComments.length) {
            const rootTop = document.querySelector('.o_knowledge_body').getBoundingClientRect().top;
            const encounteredThreadIds = {};
            this.allCommentsThreadRecords.forEach((commentThread) => {
                encounteredThreadIds[commentThread.id] = true;
                const anchors = Array.from(document.querySelectorAll(`.knowledge-thread-comment[data-id="${commentThread.id}"]`)).filter((node) => !isZWS(node));
                const targetTop = anchors[0]?.getBoundingClientRect().top;
                const comment = {
                    knowledgeThreadId: commentThread.id,
                    articleId:commentThread.article_id[0],
                    isResolved: commentThread.is_resolved,
                    anchors: anchors.length ? anchors : [],
                    top: Math.abs(rootTop - targetTop),
                    thread: this.threadService.getThread('knowledge.article.thread', commentThread.id),
                    destroyComment: this.destroyComment.bind(this),
                };

                this.changeStyling(anchors, comment.isResolved);

                this.state.comments[commentThread.id] = comment;
            });
            this.allComments.forEach((node) => {
                if (document.contains(node) && node.dataset.id &&!encounteredThreadIds[parseInt(node.dataset.id)]) {
                    const text = document.createTextNode(node.textContent);
                    node.replaceWith(text);
                }
            });
        }
    }

    /**
     *
     * @param {integer} id ID of the comment to destroy
     * @param {HTMLElement} [anchor=undefined] The text anchor of the comment being destroyed, in case it doesn't exist.
     */
    async destroyComment(id, anchor=undefined, unlink=false) {
        this.allCommentsThreadRecords = this.allCommentsThreadRecords.filter((commentThread) => commentThread.id !== id);
        if (anchor) {
            const text = document.createTextNode(anchor.textContent);
            anchor.replaceWith(text);
        }
        const toDestroy = this.state.comments[id] || this.state.comments['undefined'];
        if (!toDestroy) {
            return;
        }
        const commentAnchors = toDestroy.anchors;
        for (const commentAnchor of commentAnchors) {
            const text = document.createTextNode(commentAnchor.textContent);
            commentAnchor.replaceWith(text);
        }
        delete this.state.comments[id];
        delete this.state.comments['undefined'];
        this.env.bus.trigger('KNOWLEDGE_COMMENTS_PANELS:DELETE_COMMENT', {removedCommentId: id});
        if (unlink) {
            await this.orm.unlink('knowledge.article.thread', [id]);
        }
        await this.props.record.save();
    }

    /**============================================
     *               Thread Resolution
     *=============================================**/

    changeCommentResolvedState(ev) {
        this._changeCommentResolvedState(ev.detail.threadId, ev.detail.newResolvedState, ev);
    }

    async _changeCommentResolvedState(id, newResolvedState, ev) {
        if (!ev) {
            this.env.bus.trigger('KNOWLEDGE_COMMENTS_PANELS:CHANGE_COMMENT_STATE', {id: id, newResolvedState: newResolvedState});
        }
        if (status(this) === 'destroyed') {
            return;
        }
        // calling via the orm to ensure committing in the DB
        try {
            await this.orm.call(
                'knowledge.article.thread',
                'toggle_thread',
                [id],
                {}
            );
        } catch {
            return false;
        }
        const commentToToggle = this.state.comments[id];
        if (commentToToggle) {
            this.state.comments[id].isResolved = newResolvedState;
            this.changeStyling(commentToToggle.anchors, newResolvedState);
        }
        return true;
    }

    changeStyling(anchors, newResolvedState) {
        for (const anchor of anchors) {
            anchor.classList.remove('focused-comment');
            anchor.classList.toggle('knowledge-thread-highlighted-comment', !newResolvedState);
            if (newResolvedState) {
                anchor.removeAttribute('tabindex');
            } else {
                anchor.setAttribute('tabindex', '-1');
            }
        }
    }

    /**============================================
     *              Changes Handlers
     *=============================================**/

    handleChanges(event) {
        const impactedComments = event.detail.impactedComments;
        for (const impactedComment of impactedComments.values()) {
            this.updateAnchors(parseInt(impactedComment));
        }
    }

    async updateAnchors(id) {
        const toUpdate = this.state.comments[id];
        // Comment doesn't exist
        const anchors = Array.from(document.querySelectorAll(`.knowledge-thread-comment[data-id="${id}"]`)).filter((node) => !isZWS(node) && !node.hasAttribute('data-oe-zws-empty-inline'));
        if (!toUpdate && anchors.length) {
            const [searchedComment] = await this.orm.searchRead(
                'knowledge.article.thread',
                [
                    ['id', '=', id],
                    ['message_ids', '!=', false]
                ],
                ['id', 'article_id', 'is_resolved', 'write_date', 'message_ids'],
                {
                    order: 'write_date DESC'
                }
            );
            if (!searchedComment) {
                return;
            }
            const rootTop = document.querySelector('.o_knowledge_body').getBoundingClientRect().top;
            const targetTop = anchors[0]?.getBoundingClientRect().top;
            const comment = {
                knowledgeThreadId: searchedComment.id,
                articleId:searchedComment.article_id[0],
                isResolved: searchedComment.is_resolved,
                anchors: anchors,
                top: Math.abs(rootTop - targetTop),
                thread: this.threadService.getThread('knowledge.article.thread', searchedComment.id),
                writeDate: searchedComment.write_date
            };

            this.changeStyling(anchors, comment.isResolved);

            this.state.comments[id] = comment;
            this.env.bus.trigger('KNOWLEDGE_COMMENTS_PANELS:CREATE_COMMENT', {comment: comment});
            return;
        }
        this.updateExistingCommentAnchors(id);
    }

    updateExistingCommentAnchors(id) {
        const toUpdate = this.state.comments[id];
        if (!toUpdate) {
            return;
        }

        const anchors = Array.from(document.querySelectorAll(`.knowledge-thread-comment[data-id="${id}"]`)).filter((node) => !isZWS(node) && !node.hasAttribute('data-oe-zws-empty-inline'));

        // Comment's anchors are no longer in the body
        if (!anchors.length) {
            if (toUpdate.anchors.length && toUpdate.anchors[0].parentElement) {
                toUpdate.anchors[0].remove();
            }
            delete this.state.comments[id];
            return;
        }
        // We do not need to update the anchors since they are all technically present => No anchor was removed
        if (toUpdate.anchors.length === anchors.length && !isZWS(toUpdate.anchors[0])) {
            this.env.bus.trigger(`KNOWLEDGE_COMMENT_${id}:COMPUTE_POSITION`, {newAnchors: anchors});
            return;
        }

        for (const anchor of anchors) {
            if (isZWS(anchor) || !anchor.childNodes.length || anchor.textContent === '') {
                anchor.remove();
            }
        }
        toUpdate.anchors = anchors;
        this.state.comments[id] = toUpdate;
        this.env.bus.trigger(`KNOWLEDGE_COMMENT_${id}:COMPUTE_POSITION`, {newAnchors: anchors});
    }
}

export const knowledgeCommentsHandler = {
    component: KnowledgeCommentsHandler,
    additionalClasses: ['position-absolute', 'top-0', 'start-100', 'd-print-none']
};

registry.category('view_widgets').add('knowledge_comments_handler', knowledgeCommentsHandler);
