/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the OWL ref the to input element containing the
        'pendingGuestName'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            guestNameInputRef
        [Field/model]
            WelcomeView
        [Field/type]
            attr
        [Field/target]
            Element
        [Field/related]
            WelcomeView/welcomeViewComponents
            Collection/first
            WelcomeView/guestNameInput
`;
