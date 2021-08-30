/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether 'this' has activities ('mail.activity.mixin' server side).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasActivities
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
