/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the value to use for 'id', 'for', and 'name' attributes of
        the guest name input and its label.

        Necessary to ensure the uniqueness.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            guestNameInputUniqueId
        [Field/model]
            WelcomeView
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/isReadonly]
            true
        [Field/compute]
            o-WelcomeView-guestNameInput-
            .{+}
                {WelcomeView/getNextGuestNameInputId}
                    @record
`;
