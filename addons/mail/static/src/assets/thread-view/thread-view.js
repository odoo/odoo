/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ThreadView
        [Model/fields]
            compact
            componentHintList
            composerView
            extraClass
            hasAutoScrollOnMessageReceived
            hasMemberList
            hasSquashCloseMessages
            hasTopbar
            isComposerFocused
            isLoading
            isMemberListOpened
            isPreparingLoading
            lastMessage
            lastMessageView
            lastNonTransientMessage
            lastVisibleMessage
            loaderTimeout
            messageListView
            messageViews
            messages
            order
            replyingToMessageView
            rtcCallViewer
            thread
            threadCache
            threadCacheInitialScrollHeight
            threadCacheInitialScrollPosition
            threadCacheInitialScrollPositions
            threadViewer
            topbar
        [Model/id]
            ThreadView/threadViewer
        [Model/actions]
            ThreadView/_shouldMessageBeSquashed
            ThreadView/addComponentHint
            ThreadView/handleVisibleMessage
            ThreadView/markComponentHintProcessed
            ThreadView/startEditingLastMessageFromCurrentUser
        [Model/onChanges]
            onThreadCacheChanged
            onThreadCacheIsLoadingChanged
            onThreadShouldBeSetAsSeen
`;
