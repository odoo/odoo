/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Promise that will be resolved when messaging is initialized.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            initializedPromise
        [Field/model]
            Env
        [Field/type]
            attr
        [Field/target]
            Promise
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
        [Field/compute]
            {Record/insert}
                [Record/models]
                    Deferred
`;
