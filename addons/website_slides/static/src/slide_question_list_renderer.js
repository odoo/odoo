/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";

export class SlideQuestionListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    async onDeleteRecord(record) {
        await this.orm.unlink("slide.question", [record.resId]);
        const res = await super.onDeleteRecord(record);
        await this.props.list.model.root.save();
        return res;
    }
}
