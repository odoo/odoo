/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            buttonDiscard
        [Element/model]
            ComposerViewComponent
        [web.Element/tag]
            button
        [web.Element/type]
            button
        [Record/models]
            ComposerViewComponent/actionButton
            ComposerViewComponent/button
        [web.Element/class]
            btn
            btn-secondary
        [Element/isPresent]
            {Device/isMobile}
            .{isFalsy}
            .{&}
                @record
                .{ComposerViewComponent/hasDiscardButton}
        [Element/onClick]
            {ComposerView/discard}
                @record
                .{ComposerViewComponent/composerView}
        [web.Element/textContent]
            {Locale/text}
                Discard
        [web.Element/style]
            [web.scss/border]
                {scss/$border-width}
                solid
                {scss/lighten}
                    {scss/gray}
                        400
                    5%
            {if}
                @record
                .{ComposerViewComponent/isCompact}
                .{&}
                    @record
                    .{ComposerViewComponent/hasCurrentPartnerAvatar}
            .{then}
                [web.scss/border-radius]
                    0
                    {scss/$o-mail-rounded-rectangle-border-radius-lg}
                    {scss/$o-mail-rounded-rectangle-border-radius-lg}
                    0
`;
