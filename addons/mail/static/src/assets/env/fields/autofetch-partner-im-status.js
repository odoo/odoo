/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether a loop should be started at initialization to
        periodically fetch the im_status of all users.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            autofetchPartnerImStatus
        [Field/model]
            Env
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
