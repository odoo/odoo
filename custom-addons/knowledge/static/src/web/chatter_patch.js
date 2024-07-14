/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { Deferred, KeepLast } from "@web/core/utils/concurrency";
import { patch } from "@web/core/utils/patch";
import { Chatter } from "@mail/core/web/chatter";
import { useCallbackRecorder } from "@web/webclient/actions/action_hook";
import {
    onWillUnmount,
    useEffect,
} from "@odoo/owl";

/**
 * Knowledge articles can interact with some records with the help of the
 * @see KnowledgeCommandsService .
 * If any record in a form view has a chatter with the ability to send message
 * and/or attach files, they are a potential target for Knowledge macros.
 */
const ChatterPatch = {
    setup() {
        super.setup(...arguments);
        if (this.env.__knowledgeUpdateCommandsRecordInfo__) {
            this.knowledgeCommandsService = useService("knowledgeCommandsService");
            // Only keep the last request to register a recordInfo active.
            const keepLastRecordInfoRequest = new KeepLast();
            // Keep track of the fact that the chatter thread is ready and has
            // loaded its access rights.
            let chatterThreadReady = new Deferred();
            let previousThreadId = this.props.threadId;
            useEffect(
                // Access rights of the current thread of the chatter are
                // populated asynchronously after the chatter is mounted, this
                // method keeps track of those changes in order to determine
                // when a recordInfo request can be evaluated.
                (threadId, canPostOnReadonly, hasReadAccess, hasWriteAccess) => {
                    if (previousThreadId !== threadId) {
                        // If the chatter changes threadId, resolve the current
                        // promise keeping track of the thread state to false,
                        // so that an ongoing request to evaluate a recordInfo
                        // (related to the previous thread) will be discarded.
                        chatterThreadReady.resolve(false);
                        chatterThreadReady = new Deferred();
                    }
                    if (
                        canPostOnReadonly !== undefined &&
                        hasReadAccess !== undefined &&
                        hasWriteAccess !== undefined
                    ) {
                        // When the access rights are all loaded, the thread
                        // is ready and a recordInfo request can be evaluated.
                        chatterThreadReady.resolve(true);
                    }
                    previousThreadId = threadId;
                },
                () => [
                    this.props.threadId,
                    this.state.thread?.canPostOnReadonly,
                    this.state.thread?.hasReadAccess,
                    this.state.thread?.hasWriteAccess,
                ]
            );
            onWillUnmount(() => {
                // If there is an ongoing request to evaluate a recordInfo,
                // discard it.
                chatterThreadReady.resolve(false);
            });
            useCallbackRecorder(
                this.env.__knowledgeUpdateCommandsRecordInfo__,
                // Callback used to record the values related to the ability to
                // post messages or attach files on the current record.
                async (recordInfo) => {
                    // At each new recording request, all previous ongoing
                    // requests are discarded through the keepLast.
                    const chatterThreadReadyForRecordInfo = keepLastRecordInfoRequest.add(chatterThreadReady);
                    if (!await chatterThreadReadyForRecordInfo) {
                        // If the chatterThreadReadyForRecordInfo promise
                        // resolves to false, the recording request should be
                        // discarded.
                        return;
                    }
                    if (
                        !this.env.model.root?.resId ||
                        recordInfo.resId !== this.env.model.root.resId ||
                        recordInfo.resModel !== this.env.model.root.resModel
                    ) {
                        // Ensure that the current record matches the recordInfo
                        // candidate.
                        return;
                    }
                    // The conditions for the ability to post or attach should
                    // be the same as the ones in the Chatter template.
                    Object.assign(recordInfo, {
                        canPostMessages: this.props.threadId &&
                            this.props.hasMessageList && (
                                this.state.thread?.hasWriteAccess ||
                                (this.state.thread?.hasReadAccess && this.state.thread?.canPostOnReadonly)
                            ),
                        canAttachFiles: this.props.threadId && this.state.thread?.hasWriteAccess
                    });
                    if (this.knowledgeCommandsService.isRecordCompatibleWithMacro(recordInfo)) {
                        this.knowledgeCommandsService.setCommandsRecordInfo(recordInfo);
                    }
                }
            );
        }
    }
};

patch(Chatter.prototype, ChatterPatch);
