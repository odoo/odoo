/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessagingMenuComponent
        [Model/fields]
            device
            id
            messagingMenu
        [Model/template]
            root
                toggler
                    icon
                    loading
                    counter
                dropdownMenu
                    dropdownLoadingIcon
                    dropdownLoadingLabel
                    dropdownMenuHeader
                        tabButtonForeach
                        newMessageButtonMobile
                        headerAutogrowSeparator
                        newMessageButtonNonMobile
                        mobileNewMessageInput
                    notificationList
                    mobileNavbar
        [Model/actions]
            MessagingMenuComponent/getTabs
            MessagingMenuComponent/_onMobileNewMessageInputSelect
            MessagingMenuComponent/_onMobileNewMessageInputSource
`;
