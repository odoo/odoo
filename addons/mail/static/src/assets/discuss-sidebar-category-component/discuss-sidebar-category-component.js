/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            DiscussSidebarCategoryComponent
        [Model/fields]
            category
        [Model/template]
            root
                header
                    title
                        titleIcon
                        titleText
                    autogrow
                    commands
                        commandView
                        commandAdd
                    counter
                content
                    addingItem
                        addingItemInput
                    itemOpenForeach
                    foldedActiveItem
`;
