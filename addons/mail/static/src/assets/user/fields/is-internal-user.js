/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this user is an internal user. An internal user is
        a member of the group 'base.group_user'. This is the inverse of the
        'share' field in python.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isInternalUser
        [Field/model]
            User
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
