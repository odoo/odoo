/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            DiscussPublicView
        [Model/fields]
            channel
            isChannelTokenSecret
            shouldAddGuestAsMemberOnJoin
            shouldDisplayWelcomeViewInitially
            threadView
            threadViewer
            welcomeView
        [Model/id]
            DiscussPublicView/messaging
        [Model/actions]
            DiscussPublicView/switchToThreadView
            DiscussPublicView/switchToWelcomeView
`;
