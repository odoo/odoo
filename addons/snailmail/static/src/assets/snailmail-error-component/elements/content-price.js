/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            contentPrice
        [Element/model]
            SnailmailErrorComponent
        [Element/isPresent]
            @record
            .{SnailmailErrorComponent/snailmailErrorView}
            .{SnailmailErrorView/notification}
            .{Notification/failureType}
            .{=}
                sn_price
        [web.Element/tag]
            p
        [web.Element/class]
            mx-3
            mb-3
        [web.Element/textContent]
            {Locale/text}
                The country to which you want to send the letter is not supported by our service.
`;
