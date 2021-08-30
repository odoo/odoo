/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Language used by interface. Formatted like:
        {language ISO 2}_{country ISO 2} (eg: fr_FR).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            language
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
                code
`;
