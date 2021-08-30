/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            closeButton
        [Element/model]
            SnailmailErrorComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-secondary
            me-2
        [web.Element/onClick]
            {SnailmailErrorView/onClickClose}
                [0]
                    @record
                    .{SnailmailErrorComponent/snailmailErrorView}
                [1]
                    @ev
        [web.Element/textContent]
            {Locale/text}
                Close
`;
