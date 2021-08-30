/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            cancelLetterButton
        [Element/model]
            SnailmailErrorComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            me-2
            {if}
                @record
                .{SnailmailErrorComponent/snailmailErrorView}
                .{SnailmailErrorView/hasCreditsError}
                .{isFalsy}
            .{then}
                btn-primary
            .{else}
                btn-secondary
        [web.Element/onClick]
            {SnailmailErrorView/onClickCancelLetter}
                [0]
                    @record
                    .{SnailmailErrorComponent/snailmailErrorView}
                [1]
                    @ev
        [web.Element/textContent]
            {Locale/text}
                Cancel letter
`;
