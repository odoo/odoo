/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Discuss
        [Model/fields]
            activeId
            activeMobileNavbarTabId
            addingChannelValue
            categoryChannel
            categoryChat
            discussView
            hasThreadView
            initActiveId
            isAddingChannel
            isAddingChat
            isInitThreadHandled
            menuId
            mobileMessagingNavbarView
            notificationListView
            replyingToMessage
            replyingToMessageComposerView
            sidebarQuickSearchValue
            thread
            threadView
            threadViewer
        [Model/id]
            Discuss/messaging
        [Model/actions]
            Discuss/clearIsAddingItem
            Discuss/close
            Discuss/focus
            Discuss/handleAddChannelAutocompleteSelect
            Discuss/handleAddChannelAutocompleteSource
            Discuss/handleAddChatAutocompleteSelect
            Discuss/handleAddChatAutocompleteSource
            Discuss/onClickMobileNewChatButton
            Discuss/onClickMobileNewChannelButton
            Discuss/onClickStartAMeetingButton
            Discuss/onInputQuickSearch
            Discuss/open
            Discuss/openInitThread
            Discuss/openThread
            Discuss/threadToActiveId
`;
