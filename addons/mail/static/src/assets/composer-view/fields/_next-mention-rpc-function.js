/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the next function to execute after the current mention
        RPC is done, if any.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _nextMentionRpcFunction
        [Field/model]
            ComposerView
        [Field/type]
            attr
        [Field/target]
            Function
        [Field/default]
            undefined
`;
