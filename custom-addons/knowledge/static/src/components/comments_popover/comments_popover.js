/** @odoo-module */

import { Composer } from "@mail/core/common/composer";
import { KnowledgeCommentCreatorComposer } from '../composer/composer';
import { Thread } from "@mail/core/common/thread";
import { useService } from "@web/core/utils/hooks";

import {
    Component,
    useChildSubEnv,
    useEffect,
    useExternalListener,
    useRef,
    useState
} from '@odoo/owl';

/**
 * This Popover is used in the case of the editable zone being too small to display the full comment
 * boxes, or when an article is set to full_width.
 * It is called when a user clicks on the image that will take the place of the comment box.
 */
export class KnowledgeCommentsPopover extends Component {

    static template = 'knowledge.KnowledgeCommentsPopover';
    static props = {
        thread: {type: Object, optional: true},
        closePopover: Function,
        resolveComment: Function,
        record: Object,
        knowledgeThreadId: {type: Number, optional: true},
        close: Function,
        onKeyUp: {type: Function, optional: true},
        insertNewThread: {type: Function, optional: true}
    };
    static components = { Composer, Thread, KnowledgeCommentCreatorComposer };

    setup() {
        this.threadService = useService('mail.thread');

        this.composerRef = useRef('ComposerRef');

        this.state = useState({
            thread: this.props.thread
        });
        if (this.state.thread) {
            this.state.thread.composer.type = 'note';
        }

        useChildSubEnv({
            closeThread: this.resolveComment.bind(this),
        });

        useExternalListener(window, 'click', this.endCommenting.bind(this));

        useEffect((el) => {
            el?.querySelector('textarea').focus();
        }, () => [this.composerRef.el]);
    }

    closePopover() {
        this.props.closePopover();
    }

    resolveComment() {
        this.props.resolveComment(this.props.knowledgeThreadId);
    }

    onKeyUp(ev) {
        this.state.textInput = ev.target.value;
        this.props.onKeyUp(ev);
    }

    endCommenting(ev) {
        if (
            !ev.target.closest(`.o_knowledge_comment_box[data-id="${this.props.knowledgeThreadId}"]`) &&
            !ev.target.closest(`.knowledge-thread-comment[data-id="${this.props.knowledgeThreadId}"]`) &&
            ev.target.closest('.o_knowledge_form_view')
        ) {
            this.closePopover();
        }
    }

    async insertNewThread(value, postData) {
        await this.props.insertNewThread(value, postData);
        this.closePopover();
    }
}
