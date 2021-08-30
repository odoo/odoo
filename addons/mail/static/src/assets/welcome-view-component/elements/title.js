/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            title
        [Element/model]
            WelcomeViewComponent
        [web.Element/tag]
            h1
        [web.Element/class]
            font-weight-light
        [web.Element/textContent]
            {if}
                @record
                .{WelcomeViewComponent/welcomeView}
                .{WelcomeView/mediaPreview}
            .{then}
                {Locale/text}
                    You've been invited to a meeting!
            .{else}
                {Locale/text}
                    You've been invited to a chat!
`;
