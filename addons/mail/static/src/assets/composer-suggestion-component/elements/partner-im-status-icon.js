/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            partnerImStatusIcon
        [Element/model]
            ComposerSuggestionComponent
        [Field/target]
            PartnerImStatusIconComponent
        [web.Element/class]
            mr-1
        [Element/isPresent]
            @record
            .{ComposerSuggestionComponent/modelName}
            .{=}
                Partner
        [PartnerImStatusIconComponent/hasBackground]
            false
        [PartnerImStatusIconComponent/partner]
            @record
            .{ComposerSuggestionComponent/record}
        [web.Element/style]
            [web.scss/flex]
                0
                0
                auto
`;
