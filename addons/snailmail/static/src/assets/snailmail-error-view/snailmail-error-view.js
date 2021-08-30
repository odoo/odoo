/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            SnailmailErrorView
        [Model/fields]
            component
            dialogOwner
            hasCreditsError
            message
            notification
        [Model/id]
            SnailmailErrorView/dialogOwner
        [Model/actions]
            SnailmailErrorView/containsElement
            SnailmailErrorView/onClickCancelLetter
            SnailmailErrorView/onClickClose
            SnailmailErrorView/onClickResendLetter
`;
