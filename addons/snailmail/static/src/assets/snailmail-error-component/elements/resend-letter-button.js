/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            resendLetterButton
        [Element/model]
            SnailmailErrorComponent
        [Element/isPresent]
            @record
            .{SnailmailErrorComponent/snailmailErrorView}
            .{SnailmailErrorView/hasCreditsError}
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-primary
            me-2
        [web.Element/onClick]
            {SnailmailErrorView/onClickResendLetter}
                [0]
                    @record
                    .{SnailmailErrorComponent/snailmailErrorView}
                [1]
                    @ev
        [web.Element/textContent]
            {Locale/text}
                Re-send letter
`;
