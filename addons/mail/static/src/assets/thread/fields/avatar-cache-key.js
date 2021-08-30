/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Cache key to force a reload of the avatar when avatar is changed.
        It only makes sense for channels.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            avatarCacheKey
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            String
`;
