/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            contentError
        [Element/model]
            SnailmailErrorComponent
        [Element/isPresent]
            @record
            .{SnailmailErrorComponent/snailmailErrorView}
            .{SnailmailErrorView/notification}
            .{Notification/failureType}
            .{=}
                sn_error
        [web.Element/tag]
            p
        [web.Element/class]
            mx-3
            mb-3
        [web.Element/textContent]
            {Locale/text}
                An unknown error occurred. Please contact our <a href="https://www.odoo.com/help" target="new">support</a> for further assistance.
`;
