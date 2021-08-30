/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether 'this.threadCache' is currently loading messages.

        This field is related to 'this.threadCache.isLoading' but with a
        delay on its update to avoid flickering on the UI.

        It is computed through '_onThreadCacheIsLoadingChanged' and it should
        otherwise be considered read-only.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isLoading
        [Field/model]
            ThreadView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
