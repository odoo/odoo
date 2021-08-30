/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            DiscussSidebarCategory
        [Model/fields]
            activeItem
            autocompleteMethod
            categoryItems
            commandAddTitleText
            counter
            discussAsChannel
            discussAsChat
            filteredCategoryItems
            hasAddCommand
            hasViewCommand
            isAddingItem
            isOpen
            isPendingOpen
            isServerOpen
            name
            newItemPlaceholderText
            serverStateKey
            sortComputeMethod
            supportedChannelTypes
        [Model/id]
            DiscussSidebarCategory/discussAsChannel
            .{|}
                DiscussSidebarCategory/discussAsChat
        [Model/onChange]
            DiscussSidebarCategory/onIsServerOpenChanged
        [Model/actions]
            DiscussSidebarCategory/close
            DiscussSidebarCategory/onAddItemAutocompleteSelect
            DiscussSidebarCategory/onAddItemAutocompleteSource
            DiscussSidebarCategory/onClick
            DiscussSidebarCategory/onClickCommandAdd
            DiscussSidebarCategory/onClickCommandView
            DiscussSidebarCategory/onHideAddingItem
            DiscussSidebarCategory/open
            DiscussSidebarCategory/performRpcSetResUsersSettings
`;
