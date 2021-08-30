/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            welcomeView
        [Element/model]
            DiscussPublicViewComponent
        [Element/isPresent]
            @record
            .{DiscussPublicViewComponent/discussPublicView}
            .{DiscussPublicView/welcomeView}
        [Field/target]
            WelcomeViewComponent
        [WelcomeViewComponent/welcomeView]
            @record
            .{DiscussPublicViewComponent/discussPublicView}
            .{DiscussPublicView/welcomeView}
`;
