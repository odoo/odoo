/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether 'this' is aware of 'this.threadCache' currently
        loading messages, but 'this' is not yet ready to display that loading
        on the UI.

        This field is computed through '_onThreadCacheIsLoadingChanged' and
        it should otherwise be considered read-only.

        @see 'isLoading'
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isPreparingLoading
        [Field/model]
            ThreadView
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
