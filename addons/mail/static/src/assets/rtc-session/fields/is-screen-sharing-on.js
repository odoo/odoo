/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines if the user is sharing their screen.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isScreenSharingOn
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
