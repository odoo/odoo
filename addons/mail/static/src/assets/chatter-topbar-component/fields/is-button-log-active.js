/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isButtonLogActive
        [Field/model]
            ChatterTopbarComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            @record
            .{ChatterTopbarComponent/chatter}
            .{Chatter/composerView}
            .{&}
                @record
                .{ChatterTopbarComponent/chatter}
                .{Chatter/composerView}
                .{ComposerView/composer}
                .{Composer/isLog}
`;
