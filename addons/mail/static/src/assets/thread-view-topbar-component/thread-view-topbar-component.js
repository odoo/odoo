/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ThreadViewTopbarComponent
        [Model/fields]
            threadViewTopbar
        [Model/template]
            root
                threadIcon
                title
                    threadName
                    threadNameInput
                    noThreadName
                    threadDescriptionSeparator
                    threadDescription
                    threadAddDescriptionEmptyLabel
                    threadDescriptionInput
                actions
                    markAllReadButton
                    unstarAllButton
                    callButton
                        callButtonIcon
                    callVideoButton
                        callVideoButtonIcon
                    inviteButton
                        inviteButtonIcon
                    invitePopoverView
                    showMemberListButton
                        showMemberListButtonIcon
                    hideMemberListButton
                        hideMemberListButtonIcon
                userInfo
                    avatar
                        userName
                        guestNameInput
        [Model/lifecycle]
            onUpdate
`;
