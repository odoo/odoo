/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Chatter
        [Model/fields]
            activityBoxView
            attachmentBoxView
            attachmentsLoaderTimeout
            component
            composerView
            context
            hasActivities
            hasExternalBorder
            hasFollowers
            hasMessageList
            hasMessageListScrollAdjust
            hasParentReloadOnAttachmentsChanged
            hasThreadView
            hasTopbarCloseButton
            id
            isAttachmentBoxVisibleInitially
            isDisabled
            isPreparingAttachmentsLoading
            isShowingAttachmentsLoading
            thread
            threadId
            threadIsLoadingAttachments
            threadModel
            threadView
            threadViewer
        [Model/id]
            Chatter/id
        [Model/actions]
            Chatter/_prepareAttachmentsLoading
            Chatter/_stopAttachmentsLoading
            Chatter/focus
            Chatter/onClickLogNote
            Chatter/onClickScheduleActivity
            Chatter/onClickSendMessage
            Chatter/onScrollScrollPanel
            Chatter/refresh
            Chatter/reloadParentView
            Chatter/showLogNote
            Chatter/showSendMessage
        [Model/lifecycles]
            onDelete
        [Model/onChanges]
            onThreadIdOrThreadModelChanged
            onThreadIsLoadingAttachmentsChanged
`;
