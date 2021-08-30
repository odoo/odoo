/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            ActivityBoxComponent
        [Model/fields]
            activityBoxView
        [Model/template]
            root
                title
                    titleStartLine
                    titleText
                        titleTextIcon
                        titleTextLabel
                    titleBadges
                        titleBadgeOverdue
                        titleBadgeToday
                        titleBadgeFuture
                    titleEndLine
                activityList
                    activityViewForeach
`;
