/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the initial scroll height of thread caches, which is the
        scroll height at the time the last scroll position was saved.
        Useful to only restore scroll position when the corresponding height
        is available, otherwise the restore makes no sense.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadCacheInitialScrollHeights
        [Field/model]
            ThreadViewer
        [Field/type]
            attr
        [Field/target]
            Dict
        [Field/default]
            {Record/insert}
                [Record/models]
                    Dict
`;
