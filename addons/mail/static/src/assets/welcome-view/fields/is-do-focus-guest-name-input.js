/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the 'guestNameInput' should be focused the next
        time the component is updated.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isDoFocusGuestNameInput
        [Field/model]
            WelcomeView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
