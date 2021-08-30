/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Opens the most appropriate view that is a profile for this thread.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/openProfile
        [Action/params]
            thread
                [type]
                    Thread
        [Action/behavior]
            {Env/openDocument}
                [id]
                    @thread
                    .{Thread/id}
                [model]
                    @thread
                    .{Thread/model}
`;
