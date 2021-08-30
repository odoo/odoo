/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the pending description of this thread, which is the new description of
        the thread as the current user is currently typing it, with the goal
        of changing the description the thread.
        This value can either be applied or discarded.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            pendingThreadDescription
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            String
`;
