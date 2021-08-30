/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Text for followers
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            followers
        [Element/model]
            ComposerViewComponent
        [web.Element/tag]
            small
        [Element/isPresent]
            @record
            .{ComposerViewComponent/hasFollowers}
            .{&}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/composer}
                .{Composer/isLog}
                .{isFalsy}
        [web.Element/htmlContent]
            {if}
                @record
                .{ComposerViewComponent/composerView}
                .{ComposerView/composer}
                .{Composer/activeThread}
                .{Thread/displayName}
                .{isFalsy}
            .{then}
                {Locale/text}
                    <b class="text-muted">To: </b>
                    <em class="text-muted">Followers of </em>
                    <b>this document</b>
            .{else}
                {String/sprintf}
                    [0]
                        {Locale/text}
                            <b class="text-muted">To: </b>
                            <em class="text-muted">Followers of </em>
                            <b>&#32;&quot;%s&quot;</b>
                    [1]
                        @record
                        .{ComposerViewComponent/composerView}
                        .{ComposerView/composer}
                        .{Composer/activeThread}
                        .{Thread/displayName}
        [web.Element/style]
            [web.scss/flex]
                0
                0
                100%
            [web.scss/margin-bottom]
                {scss/$o-mail-chatter-gap}
                .{*}
                    0.5
`;
