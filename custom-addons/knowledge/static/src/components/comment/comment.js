/** @odoo-module */
import { useBus, useService } from '@web/core/utils/hooks';
import { usePopover } from '@web/core/popover/popover_hook';
import { Composer } from '@mail/core/common/composer';
import { Thread } from '@mail/core/common/thread';
import { KnowledgeCommentsPopover } from '../comments_popover/comments_popover';
import { KnowledgeCommentCreatorComposer } from '../composer/composer';
import { closestBlock } from '@web_editor/js/editor/odoo-editor/src/utils/utils';
import { _t } from '@web/core/l10n/translation';

import {
    Component,
    onMounted,
    onPatched,
    onWillStart,
    onWillUpdateProps,
    useChildSubEnv,
    useExternalListener,
    useRef,
    useEffect,
    useState
} from '@odoo/owl';

export class KnowledgeCommentsThread extends Component {

    static components = { Composer, Thread, KnowledgeCommentCreatorComposer };
    static props = {
        articleId: {type: Number, optional: true},
        anchors: {type: Array, optional: true},
        changeCommentResolvedState: Function,
        destroyComment: Function,
        forceFullSize: {type: Boolean, optional: true},
        insertNewThread: {type: Function, optional: true},
        isCreationMode: {type: Boolean, optional: true},
        isResolved: Boolean,
        knowledgeThreadId: {type: Number, optional: true},
        /**@see \@web/model/relational_model/record */
        record: Object,
        /**@see \@mail/core/common/thread_model*/
        thread: {type: Object, optional: true},
        top: {type: Number, optional: true},
        writeDate: {optional: true}
    };
    static template = 'knowledge.KnowledgeCommentsThread';

    setup() {
        this.targetRef = useRef('targetRef');

        this.threadService = useService('mail.thread');
        this.messageService = useService('mail.message');
        this.userService = useService('user');
        this.orm = useService('orm');
        this.uiService = useService('ui');
        this.popover = usePopover(KnowledgeCommentsPopover, {
            closeOnClickAway: false,
            position: 'bottom-start',
            popoverClass: 'overflow-auto mh-50 o_knowledge_comments_popover'
        });

        this.messages = [];

        this.composerDivRef = useRef('composerDivRef');

        // Array of all the anchors linked to a single comment
        this.anchors = this.props.anchors;
        // Main anchor used for the positioning
        this.mainAnchor = this.anchors[0];

        this.state = useState({
            loading: true,
            commenting: false,
            thread: this.props.thread,
            isResolved: this.props.isResolved,
            smallUI: !this.props.forceFullSize &&
                (
                    this.props.record.data.full_width ||
                    this.isSmallUINeeded()
                ),
            // This array contains the text of the anchors selected by the user to create the comment.
            // Each element of this array corresponds to the text of a paragraph.
            quotes: [],
            knowledgeThreadId: this.props.knowledgeThreadId,
            top: this.props.top
        });

        useChildSubEnv({
            // We need to unset the chatter inside the env of the child Components
            // because this Object contains values and methods that are linked to the form view's
            // main chatter. By doing this we distinguish the main chatter from the comments.
            chatter: false,
            closeThread: this.resolveComment.bind(this),
            openThread: this.unresolveComment.bind(this),
            isResolved: this.isResolved
        });

        this.placeholder = _t('Add a Comment...');

        useBus(this.uiService.bus, 'resize', () => {
            this.state.smallUI = this.isSmallUINeeded();
        });
        useBus(this.env.bus, `KNOWLEDGE_COMMENT_${this.state.knowledgeThreadId}:HIGHLIGHT`, () => {
            this.state.commenting = true;
            if (!this.state.isResolved && this.state.smallUI) {
                this.openPopover({ target: this.targetRef.el });
            }
            this.highlightComment(true);
        });
        useBus(this.env.bus, `KNOWLEDGE_COMMENT_${this.state.knowledgeThreadId}:COMPUTE_POSITION`, ({detail}) => {
            if (detail) {
                this.anchors = detail.newAnchors;
                this.mainAnchor = this.anchors[0];
            }
            const oldTop = this.top;
            this.setTopPosition();
            // Only update the position if we have a significant change to avoid flickers
            if (Math.abs(oldTop - this.top) > this.mainAnchor.getBoundingClientRect().height) {
                this.state.top = this.top;
            }
        });
        useBus(this.env.bus, 'KNOWLEDGE:CLOSE_COMMENT', () => this.state.commenting = false);
        useBus(this.env.bus, 'mail.thread/onUpdate', ({ detail }) => {
            if (detail.data.isLoaded && detail.thread.model === 'knowledge.article.thread') {
                this.state.lastPartnerId = detail.thread.messages.at(-1)?.author.id || this.userService.partnerId;
            }
        });

        /**
         * This observer checks for mutation inside the previous sibling of the box and the box itself.
         */
        this.observer = new MutationObserver(() => {
            if (this.targetRef.el) {
                const oldTop = this.top;
                if (!this.mainAnchor?.parentNode) {
                    return;
                }

                this.setTopPosition();
                // Only update the position if we have a significant change to avoid flickers
                if (Math.abs(oldTop - this.top) > this.mainAnchor?.getBoundingClientRect().height) {
                    this.state.top = this.top;
                }
            }
        });

        useExternalListener(window, 'click', this.endCommenting.bind(this));

        onWillUpdateProps((nextProps) => {
            this.anchors = nextProps.anchors;
            this.mainAnchor = nextProps.anchors[0];
        });
        onMounted(() => {
            this.state.loading = false;
            this.highlightComment(false);
            // If the ID of the thread is 0 it is considered as a virtual comment, it is in the
            // phase of being created but doesn't exist currently. This way we avoid creating records
            // that will not
            if (this.props.isCreationMode) {
                this.state.commenting = true;
                if (this.state.smallUI) {
                    this.openPopover({target: this.targetRef.el});
                } else {
                    this.composerDivRef.el.querySelector('textarea')?.focus();
                }
                this.highlightComment(true);
            }
            const paragraphs = new Map();
            for (const anchor of this.anchors) {
                const closestParagraph = closestBlock(anchor);
                if (!paragraphs.has(closestParagraph)) {
                    paragraphs.set(closestParagraph, anchor.textContent);
                } else {
                    paragraphs.set(closestParagraph, paragraphs.get(closestParagraph) + anchor.textContent);
                }
            }
            this.state.quotes = Array.from(paragraphs.values());
            if (!this.props.forceFullSize) {
                if (this.state.isResolved && this.mainAnchor?.classList.contains('highlighted-comment')) {
                    this.resolveComment();
                    return;
                }
                this.setTopPosition();
                if (this.targetRef.el) {
                    this.state.top = this.top;
                    this.targetRef.el.closest('.o_scroll_view_lg').addEventListener('scroll', this.onScroll.bind(this));
                }
            }
        });

        onPatched(() => {
            if (this.autoFocusTextarea) {
                this.composerDivRef.el?.querySelector('textarea')?.focus();
                this.autoFocusTextarea = false;
            }
            const { messages } = this.threadService.store.get(this.state.thread.localId);
            if (messages.length && messages.every((message) => !message.body)) {
                this.props.destroyComment(this.state.knowledgeThreadId, this.mainAnchor, true);
                return;
            }
            if (!this.props.forceFullSize) {
                this.setTopPosition();
                this.updateHorizontalDimensions();
                if (this.targetRef.el) {
                    this.state.top = this.top;
                }
            }
        });

        onWillStart(async () => {
            this.messages = await this.threadService.fetchMessages(this.state.thread);
            if (this.state.smallUI && this.state.thread) {
                const nonEmptyMessages = this.messages.some((message) => message.body);
                if (this.messages.length && !nonEmptyMessages) {
                    this.props.destroyComment(this.state.knowledgeThreadId, this.mainAnchor, true);
                    return;
                }
                this.state.lastPartnerId = this.messages.length ? this.messages.at(-1)?.author.id : this.userService.partnerId;
            } else if (!this.state.thread) {
                this.state.lastPartnerId = this.userService.partnerId;
            }
        });

        useEffect(() => {
            if (!this.state.smallUI && this.props.knowledgeThreadId) {
                const observer = new MutationObserver((mutationList) => {
                    const mutationsWithEmptyThread = mutationList.some((mutation) => mutation.target.querySelector('.o-mail-Thread-empty'));
                    if (mutationsWithEmptyThread) {
                        this.props.destroyComment(this.state.knowledgeThreadId, this.mainAnchor, true);
                        return;
                    }
                });
                observer.observe(this.targetRef.el.querySelector('.o-mail-Thread'), {subtree:true, childList: true});
                return () => observer.disconnect();
            }

        }, () => []);

        useEffect((isFullWidth) => {
            this.state.smallUI = isFullWidth;
            this.updateHorizontalDimensions(isFullWidth);
        }, () => [this.props.record.data.full_width]);

        if (!this.props.forceFullSize) {
            useEffect(() => {
                const observer = new ResizeObserver(() => {
                    this.updateHorizontalDimensions();
                });
                observer.observe(this.editable.parentElement);
                return () => observer.disconnect();
            }, () => []);
            useEffect((el, sibling, childNodes) => {
                if (el) {
                    this.observer.observe(el, {subtree: true, childList: true});
                    this.observer.observe(el.parentElement, {childList: true, subtree: true, attributeFilter: ['style']});
                }
                let removeEventListener = false;
                if (sibling) {
                    this.observer.observe(sibling, {subtree: true, attributeFilter: ['style'], attributeOldValue: true});
                    if (sibling.querySelector('.o_knowledge_comment_box_thread')) {
                        this.observer.observe(sibling.querySelector('.o_knowledge_comment_box_thread'), {childList: true, subtree:true});
                    }
                    const composerDivContainer = sibling.querySelector('.o_knowledge_comments_buttons');
                    if (composerDivContainer) {
                        composerDivContainer.addEventListener('input', () => {
                            this.setTopPosition();
                            if (this.targetRef.el) {
                                this.state.top = this.top;
                            }
                        });
                        removeEventListener = () => composerDivContainer.removeEventListener('input', () => {
                            this.setTopPosition();
                            if (this.targetRef.el) {
                                this.state.top = this.top;
                            }
                        });
                    }
                }
                return () => {
                    if (removeEventListener) {
                        removeEventListener();
                    }
                    this.observer.disconnect();
                };
            }, () => {
                if (!this.targetRef.el?.previousElementSibling) {
                    return [this.targetRef.el];
                }
                return [this.targetRef.el, this.targetRef.el.previousElementSibling];
            });
        }
    }

    /**======================
     *    Getters
     *========================**/

    get editable() {
        return document.querySelector(
            `.o_field_html .note-editable,
            .o_field_knowledge_article_html_field .note-editable,
            .o_field_knowledge_article_html_field .o_readonly`
        );
    }
    /**
     * Used for the message actions
     */
    get isResolved() {
        return this.state.isResolved;
    }

    get textInputContent() {
        return this.props.knowledgeThreadId && this.state.thread.composer.textInputContent;
    }


    /**======================
     *  Position Computations
     *========================**/

    isSmallUINeeded() {
        const maxWidth = this.editable.closest('.o_field_knowledge_article_html_field').getBoundingClientRect().right - this.editable.getBoundingClientRect().right;
        return maxWidth <= 300;
    }

    onScroll() {
        if (this.props.forceFullSize || !this.targetRef.el) {
            return;
        }
        const oldTop = this.top;
        if (!this.mainAnchor?.parentNode) {
            return;
        }
        this.setTopPosition();
        if (this.targetRef.el && Math.abs(oldTop - this.top) > this.mainAnchor?.getBoundingClientRect().height) {
            this.targetRef.el.style.top = `${this.top}px`;
        }
    }

    /**
     * This function computes the vertical position of the comment box and sets the variable this.top
     * to the new top value that the box should be positioned at.
     * To compute the position we take into account the top position of the anchor and we check if
     * at this position we don't intersect with any other box. If that's the case then the new top
     * position is the bottom of the intersected box, this way we do not have any intersections
     * between them.
     */
    setTopPosition() {
        if (!this.targetRef.el) {
            return;
        }
        const rootTop = document.querySelector('.o_knowledge_body').getBoundingClientRect().top;
        if (!this.mainAnchor?.parentNode) {
            return;
        }
        const targetTop = this.mainAnchor.getBoundingClientRect().top;
        const newTop = Math.abs(rootTop - targetTop);
        const sibling = this.targetRef.el.previousElementSibling;
        if (!sibling) {
            this.top = Math.round(newTop);
            return;
        }
        const siblingRect = sibling.getBoundingClientRect();
        const needsRepositioning = targetTop < siblingRect.bottom;
        // 2 is to add a space between boxes, it is so that they are not directly set one below the other
        const previousBottom = siblingRect.bottom - rootTop + 2;

        this.top = Math.round(!needsRepositioning ? newTop : previousBottom);
    }

    /**
     * This functions redimensions horizontally the Component to let it fit in the right column.
     * @param {boolean} forcedSmallUI Do we need to force the small UI to the component
     */
    updateHorizontalDimensions(forcedSmallUI=false) {
        if (!this.targetRef.el || !this.editable) {
            return;
        }
        // 400px is the maxWidth set in the css file for the class .o_knowledge_comment_box.
        const boxMaxWidth = 400;
        const limitRight = this.editable.parentElement.getBoundingClientRect().right;
        const maxWidth = limitRight - this.editable.getBoundingClientRect().right;
        const commentWidth = this.targetRef.el.getBoundingClientRect().width;
        this.state.smallUI = !this.props.forceFullSize && (forcedSmallUI || this.isSmallUINeeded());
        if (this.state.smallUI) {
            this.state.lastPartnerId = this.messages.at(-1)?.author.id || this.userService.partnerId;
            this.state.width = '';
            // 1cm is the size of the margin that was decided to set when an article is not full size but
            // still triggers the small UI mode. 1rem is the size of the
            this.state.marginRight = this.props.record.data.full_width ? 'margin-right: 1rem' : 'margin-right: 1cm';
            return;
        }
        if (this.popover.isOpen) {
            this.popover.close();
        }
        this.originalWidth = this.originalWidth ? this.originalWidth : boxMaxWidth;
        if (maxWidth > boxMaxWidth) {
            this.state.marginRight = `margin-right: ${ maxWidth/2 - boxMaxWidth/2 }px`;
            this.state.width = `width: ${ boxMaxWidth }px`;
        } else {
            this.state.width = `width: ${ commentWidth - (commentWidth - maxWidth) }px`;
            this.state.marginRight = this.props.record.data.full_width ? '' : 'margin-right: 1cm';
        }
    }

    /**======================
     *    Popover actions
     *========================**/

    closePopover() {
        this.popover.close();
        this.state.commenting = false;
        this.highlightComment(false);
        this.mainAnchor?.dispatchEvent(new Event('focusout'));
    }


    openPopover(ev) {
        if (!this.popover.isOpen) {
            this.state.commentingId = true;
            const popoverProps = {
                knowledgeThreadId: this.state.knowledgeThreadId,
                record: this.props.record,
                thread: this.state.thread,
                closePopover: this.closePopover.bind(this),
                resolveComment: this.resolveComment.bind(this),
                insertNewThread: this.insertNewThread.bind(this)
            };
            this.popover.open(ev.target.closest('.o_knowledge_comment_box'), popoverProps);
        }
    }

    /**======================
     *    Comment Actions
     *========================**/

    endCommenting(ev) {
        if (
            this.state.commenting &&
            (
                !ev.target.closest(`.o_knowledge_comment_box[data-id="${this.props.knowledgeThreadId}"]`) &&
                !(
                    this.props.isCreationMode &&
                    ev.target.closest('.o_knowledge_comment_box') &&
                    !ev.target.closest('.o_knowledge_comment_box').dataset.id
                )
            ) &&
            (
                !ev.target.closest(`.knowledge-thread-comment[data-id="${this.props.knowledgeThreadId}"]`) &&
                !(
                    this.props.isCreationMode && ev.target.closest('.knowledge-thread-comment') &&
                    !ev.target.closest('.knowledge-thread-comment').dataset.id
                )
            ) &&
            ev.target.closest('.o_knowledge_form_view') &&
            !this.textInputContent
        ) {
            this.state.commenting = false;
            this.highlightComment(false);
            this.targetRef.el.classList.remove('commenting', 'focused-comment');
            this.targetRef.el.querySelector('a[data-type="cancel"]')?.click();
            if (!this.state.thread?.messages.length) {
                if (!this.props.knowledgeThreadId) {
                    this.threadService.clearComposer(this.state.thread.composer);
                }
                this.props.destroyComment(this.state.knowledgeThreadId, this.mainAnchor);
            }
        }
    }

    showAnchors() {
        this.mainAnchor?.scrollIntoView({
            behavior: 'smooth',
            block: 'center'
        });
        this.highlightComment(true);
        window.setTimeout(() => this.highlightComment(false), 500);
    }

    startCommenting(ev) {
        if (
            (
                ev.target.closest(`.comment[data-id="${this.state.knowledgeThreadId}"]`) ||
                ev.target.closest(`.o_knowledge_comment_box[data-id="${this.state.knowledgeThreadId}"]`)
            ) &&
            !ev.target.closest('.o-mail-Message-actions, .o-mail-Message-content .o-mail-Composer, .o-mail-MessageReaction, .o-mail-Composer ~ span a')
        ) {
            if (!this.state.smallUI) {
                this.autoFocusTextarea = true;
            }
            this.state.commenting = true;
            if (!this.state.isResolved && this.state.smallUI && !this.props.forceFullSize) {
                this.openPopover({target: this.targetRef.el});
            }
            this.highlightComment(true);
        }
    }

    /**========================================================================
 *                            Resolution State Thread
     *========================================================================**/

    highlightComment(isHighlighted) {
        if (!this.props.forceFullSize) {
            if (isHighlighted || this.state.commenting) {
                this.targetRef.el?.classList.add('focused-comment');
            } else {
                this.targetRef.el?.classList.remove('focused-comment');
            }
        }
        if (this.anchors) {
            for (const anchor of this.anchors) {
                if (isHighlighted || this.state.commenting) {
                    anchor.classList.add('focused-comment');
                } else {
                    anchor.classList.remove('focused-comment');
                }
            }
        }
    }

    /**
     * This function enables the user to resolve a thread. A resolved thread is a thread where the
     * user considers that the discussion does not need to go any further, thus closing it and making
     * its box disappear. These closed discussions can still be found in the panel if need be.
     * @returns
     */
    async resolveComment() {
        const statusChanged = await this.props.changeCommentResolvedState(this.state.knowledgeThreadId, true);
        if (!statusChanged) {
            return;
        }
        this.state.isResolved = true;
        if (this.props.forceFullSize) {
            this.messages = await this.threadService.fetchNewMessages(this.state.thread);
        }
    }
    /**
     * This function enables the user to unresolve a thread making it again visible to other users.
     * @returns
     */
    async unresolveComment() {
        const statusChanged = await this.props.changeCommentResolvedState(this.state.knowledgeThreadId, false);
        if (!statusChanged) {
            return;
        }
        this.state.isResolved = false;
        if (this.props.forceFullSize) {
            this.messages = await this.threadService.fetchNewMessages(this.state.thread);
        }
    }

    /**======================
     *    Comment Creation
     *========================**/

    async insertNewThread(value, postData) {
        if (!value) {
            return;
        }
        const [id] = await this.orm.create(
            'knowledge.article.thread',
            [{ article_id: this.props.record.resId }],
            {}
        );
        this.threadService.clearComposer(this.state.thread.composer);
        this.state.thread = this.threadService.getThread('knowledge.article.thread', id);
        this.threadService.post(this.state.thread, value, postData);
        for (const anchor of this.anchors) {
            anchor.dataset.id = id;
        }
        this.highlightComment(false);
        await this.props.insertNewThread(id, this.state.thread);
        this.state.updating = true;
    }
}
