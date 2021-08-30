/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the value of the 'guestNameInput'.

        Will be used to update the current guest's name when joining the
        channel by clicking on the 'joinButton'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            pendingGuestName
        [Field/model]
            WelcomeView
        [Field/type]
            attr
        [Field/target]
            String
`;
