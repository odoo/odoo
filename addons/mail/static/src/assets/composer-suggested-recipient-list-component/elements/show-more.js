/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            showMore
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
        [Element/onClick]
            {Record/update}
                [0]
                    @record
                [1]
                    [ComposerSuggestedRecipientListComponent/hasShowMoreButton]
                        true
        [web.Element/textContent]
            {Locale/text}
                Show more
`;
