/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ThreadCache
        [Model/fields]
            fetchedMessages
            hasLoadingFailed
            hasToLoadMessages
            isAllHistoryLoaded
            isCacheRefreshRequested
            isLoaded
            isLoading
            isLoadingMore
            isMarkAllAsReadRequested
            lastFetchedMessage
            lastMessage
            messages
            orderedFetchedMessages
            orderedMessages
            orderedNonEmptyMessages
            thread
            threadViews
        [Model/id]
            ThreadCache/thread
        [Model/actions]
            ThreadCache/_loadMessages
            ThreadCache/loadMoreMessages
            ThreadCache/loadNewMessages
        [Model/onChanges]
            onChangeForHasToLoadMessages
            onChangeMarkAllAsRead
            onHasToLoadMessagesChanged
`;
