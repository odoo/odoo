/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether 'this' should load initial messages.
        @see 'onChangeForHasToLoadMessages' value of this field is mainly set
        from this "on change".
        @see 'isCacheRefreshRequested' to request manual refresh of messages.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasToLoadMessages
        [Field/model]
            ThreadCache
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
