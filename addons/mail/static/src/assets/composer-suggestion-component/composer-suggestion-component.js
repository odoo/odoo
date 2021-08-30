/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ComposerSuggestionComponent
        [Model/fields]
            composerView
            isActive
            modelName
            record
        [Model/template]
            root
                part1CannedResponse
                part2CannedResponse
                part1Channel
                part1Command
                part2Command
                partnerImStatusIcon
                part1Partner
                part2Partner
        [Model/lifecycles]
            onUpdate
`;
