/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            threadName
        [Element/model]
            ComposerViewComponent
        [web.Element/tag]
            span
        [Element/isPresent]
            @record
            .{ComposerViewComponent/hasThreadName}
        [web.Element/htmlContent]
            {String/sprintf}
                [0]
                    {Locale/text}
                        on: <b>%s</b>
                [1]
                    @record
                    .{ComposerViewComponent/composerView}
                    .{ComposerView/composer}
                    .{Composer/activeThread}
                    .{Thread/displayName}
`;
