/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            currentGuestAvatar
        [Element/model]
            ComposerViewComponent
        [Record/models]
            ComposerViewComponent/currenAvatar
        [web.Element/alt]
            {Locale/text}
                Avatar of guest
        [Element/isPresent]
            {Env/currentGuest}
            .{&}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/composer}
                .{Composer/activeThread}
                .{Thread/model}
                .{=}
                    mail.channel
        [web.Element/src]
            /mail/channel/
            .{+}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/composer}
                .{Composer/activeThread}
                .{Thread/id}
            .{+}
                /guest/
            .{+}
                {Env/currentGuest}
                .{Guest/id}
            .{+}
                /avatar_128?unique=
            .{+}
                {Env/currentGuest}
                .{Guest/name}
`;
