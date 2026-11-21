import { ListRenderer } from "@web/views/list/list_renderer";

export class InventoryListRenderer extends ListRenderer {
    async onCellKeydown(ev, group, record) {
        // check that the enter key has been pressed
        const isCountedCell = Boolean(ev.target.closest('td[name="inventory_quantity"]'));
        if (ev.key != "Enter" || !isCountedCell) {
            return super.onCellKeydown(ev, group, record);
        }
        // find the next record and return if it doesn't exist
        const records = this.props.list.records
        const currentIndex = records.indexOf(record)
        if (currentIndex == records.length - 1) {
            return
        }
        // move to the column in the next record
        const nextRecord = records[currentIndex + 1]
        const column = this.columns.find((col) => col.name === "inventory_quantity");
        await this.onCellClicked(nextRecord, column, ev);
    }
}