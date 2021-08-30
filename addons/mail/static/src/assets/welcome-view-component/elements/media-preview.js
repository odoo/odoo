/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mediaPreview
        [Element/model]
            WelcomeViewComponent
        [web.Element/target]
            MediaPreviewComponent
        [Element/isPresent]
            @record
            .{WelcomeViewComponent/welcomeView}
            .{WelcomeView/mediaPreview}
        [MediaPreviewComponent/mediaPreview]
            @record
            .{WelcomeViewComponent/welcomeView}
            .{WelcomeView/mediaPreview}
        [web.Element/class]
            mr-5
`;
