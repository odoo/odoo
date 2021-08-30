/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns whether the given node is self or a children of self, including
        the suggestion menu.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AutocompleteInputComponent/contains
        [Action/params]
            record
            node
        [Action/behavior]
            {if}
                @record
                .{AutocompleteInputComponent/root}
                .{web.Element/contains}
                    @node
            .{then}
                true
            .{elif}
                @record
                .{AutocompleteInputComponent/customClass}
                .{isFalsy}
            .{then}
                false
            .{else}
                @record
                .{web.Element/contains}
                    @node
`;
