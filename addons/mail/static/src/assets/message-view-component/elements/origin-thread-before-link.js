/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            originThreadBeforeLink
        [Element/model]
            MessageViewComponent
        [web.Element/tag]
            span
        [web.Element/textContent]
            {if}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/message}
                .{Message/originThread}
                .{Thread/model}
                .{=}
                    mail.channel
            .{then}
                {Locale/text}
                    (from 
            .{else}
                {Locale/text}
                    on 
`;
