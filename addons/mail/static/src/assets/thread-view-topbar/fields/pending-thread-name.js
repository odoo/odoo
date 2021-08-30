/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the pending name of this thread, which is the new name of
        the thread as the current user is currently typing it, with the goal
        of renaming the thread.
        This value can either be applied or discarded.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            pendingThreadName
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            String
`;
