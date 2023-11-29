/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onWillStart } from "@odoo/owl";

export class MailingContactListRenderer extends ListRenderer {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        onWillStart(async () => {
            this.nameIsSplit = await this.orm.call("mailing.contact", "get_name_is_split", [], {});
            // As the columns are processed before onWillStart, reprocess them if name is split.
            if (this.nameIsSplit) {
                this.allColumns = this.processAllColumn(
                    this.props.archInfo.columns,
                    this.props.list
                );
                this.state.columns = this.getActiveColumns(this.props.list);
            }
        });
    }

    processAllColumn(allColumns, list) {
        const cols = super.processAllColumn(...arguments);
        for (const col of cols) {
            if (["first_name", "last_name"].includes(col.name)) {
                col.column_invisible = this.nameIsSplit ? "0" : "1";
            }
            if (col.name === "name") {
                col.column_invisible = this.nameIsSplit ? "1" : "0";
            }
        }
        return cols;
    }
}
