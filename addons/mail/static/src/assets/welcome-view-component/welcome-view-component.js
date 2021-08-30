/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            WelcomeViewComponent
        [Model/fields]
            welcomeView
        [Model/template]
            root
                title
                companyName
                content
                    mediaPreview
                    subContent
                        guestNameLabel
                        guestNameInput
                        loggedAsStatus
                        joinButton
        [Model/lifecycles]
            onUpdate
`;
