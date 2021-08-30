/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ChatWindowHeaderComponent
        [Model/fields]
            chatWindow
            hasCloseAsBackButton
            isExpandable
        [Model/template]
            root
                commandCloseAsBack
                    commandCloseAsBackIcon
                icon
                name
                counter
                autogrowSeparator
                rightArea
                    commandCamera
                        commandCameraIcon
                    commandPhone
                        commandPhoneIcon
                    commandShowInviteForm
                        commandShowInviteFormIcon
                    commandHideInviteForm
                        commandHideInviteFormIcon
                    commandShowMemberList
                        commandShowMemberListIcon
                    commandHideMemberList
                        commandHideMemberListIcon
                    commandShiftPrev
                        commandShiftPrevIcon
                    commandShiftNext
                        commandShiftNextIcon
                    commandExpand
                        commandExpandIcon
                    commandCloseNotAsBack
                        commandCloseNotAsBackIcon
`;
