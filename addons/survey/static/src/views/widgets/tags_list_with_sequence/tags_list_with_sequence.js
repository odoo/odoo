import { TagsList } from "@web/core/tags_list/tags_list";
import { onWillUpdateProps } from "@odoo/owl";

/**
 * Order a tag list by sequence ASC
 */
export class TagsListWithSequence extends TagsList {
    setup() {
        super.setup();

        onWillUpdateProps((nextProps) => {
            nextProps.tags.sort((a, b) => a.sequence - b.sequence);
        });
    }
}
