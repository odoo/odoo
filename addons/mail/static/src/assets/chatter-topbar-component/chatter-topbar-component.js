/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ChatterTopbarComponent
        [Model/fields]
            chatter
            isButtonSendActive
            isButtonLogActive
        [Model/template]
            root
                actions
                    buttonSendMessage
                    buttonLogNote
                    buttonScheduleActivity
                        buttonScheduleActivityIcon
                        buttonScheduleActivityLabel
                    autogrowSeparation
                    rightSection
                        buttonAttachments
                            buttonAttachmentsIcon
                            buttonAttachmentsCount
                            buttonAttachmentsCountLoader
                        followButton
                        followerListMenu
                buttonClose
                    buttonCloseIcon
`;
