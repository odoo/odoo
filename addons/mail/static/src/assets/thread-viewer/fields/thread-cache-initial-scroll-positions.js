/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the initial scroll positions of thread caches.
        Useful to restore scroll position on changing back to this
        thread cache. Note that this is only applied when opening
        the thread cache, because scroll position may change fast so
        save is already throttled.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadCacheInitialScrollPositions
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
