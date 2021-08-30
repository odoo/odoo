/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns the name of the given partner in the context of this thread.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/getMemberName
        [Action/params]
            record
                [type]
                    Thread
            partner
                [type]
                    Partner
        [Action/returns]
            String
        [Action/behavior]
            @record
            .{Thread/partner}
            .{Partner/nameOrDisplayName}
`;
