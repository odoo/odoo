/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            showLess
        [Element/model]
            ComposerSuggestedRecipientListComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-sm
            btn-link
        [Element/isPresent]
            @record
            .{ComposerSuggestedRecipientListComponent/thread}
            .{&}
                @record
                .{ComposerSuggestedRecipientListComponent/thread}
                .{Thread/suggestedRecipientInfoList}
                .{Collection/length}
                .{>}
                    3
            .{&}
                @record
                .{ComposerSuggestedRecipientListComponent/hasShowMoreButton}
                .{isFalsy}
        [Element/onClick]
            {Record/update}
                [0]
                    @record
                [1]
                    [ComposerSuggestedRecipientListComponent/hasShowMoreButton]
                        false
        [web.Element/textContent]
            {Locale/text}
                Show less
`;
