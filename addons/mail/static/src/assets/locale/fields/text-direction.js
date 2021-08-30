/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            textDirection
        [Field/model]
            Locale
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            @env
            .{Env/owlEnv}
            .{Dict/get}
                database
            .{Dict/get}
                parameters
            .{Dict/get}
                direction
`;
