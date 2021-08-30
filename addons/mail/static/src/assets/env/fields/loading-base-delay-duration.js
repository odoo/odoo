/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines after how much time in ms a "loading" indicator should be
        shown. Useful to avoid flicker for almost instant loading.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            loadingBaseDelayDuration
        [Field/model]
            Env
        [Field/type]
            attr
        [Field/target]
            Integer
        [Field/default]
            400
`;
