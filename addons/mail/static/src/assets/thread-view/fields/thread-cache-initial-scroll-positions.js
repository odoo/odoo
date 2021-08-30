/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        List of saved initial scroll positions of thread caches.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadCacheInitialScrollPositions
        [Field/model]
            ThreadView
        [Field/type]
            attr
        [Field/related]
            ThreadView/threadViewer
            ThreadViewer/threadCacheInitialScrollPositions
        [Field/default]
            {Record/insert}
                [Record/models]
                    Dict
`;
