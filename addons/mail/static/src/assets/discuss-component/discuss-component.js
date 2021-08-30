/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            DiscussComponent
        [Model/fields]
            _lastThreadCache
            _lastThreadCounter
            discussView
        [Model/template]
            root
                sidebar
                mobileMailboxSelection
                mobileAddItemHeader
                    mobileAddItemHeaderInput
                threadMobile
                noThreadMobile
                mobileNewChatButton
                mobileNewChannelButton
                notificationList
                mobileNavbar
                replyingToMessageComposerMobile
                content
                    threadNonMobile
                    noThreadNonMobile
        [Model/actions]
            DiscussComponent/_updateLocalStoreProps
            DiscussComponent/getMobileNavbarTabs
            DiscussComponent/_onMobileAddItemHeaderInputSelect
            DiscussComponent/_onMobileAddItemHeaderInputSource
        [Model/lifecycles]
            onPatched
            onUpdate
            onWillUnmount
`;
