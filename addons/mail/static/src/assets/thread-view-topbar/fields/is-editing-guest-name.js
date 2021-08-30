/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the guest is currently being renamed.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isEditingGuestName
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
