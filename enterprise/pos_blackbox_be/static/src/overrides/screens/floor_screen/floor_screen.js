import { patch } from "@web/core/utils/patch";
import { FloorScreen } from "@pos_restaurant/app/floor_screen/floor_screen";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

patch(FloorScreen.prototype, {
    async deleteFloorOrTable() {
        if (this.pos.useBlackBoxBe()) {
            let tablesToDelete = this.selectedTables;
            if (this.selectedTables.length == 0) {
                tablesToDelete = this.activeFloor.tables;
            }
            if (!this.canDeleteTable(tablesToDelete)) {
                await this.dialog.add(AlertDialog, {
                    title: _t("Delete Error"),
                    body: _t(
                        "You can't delete all tables. At least one table must remain in the configuration."
                    ),
                });
                return;
            }
        }
        return await super.deleteFloorOrTable(...arguments);
    },
    canDeleteTable(tables) {
        if (this.pos.useBlackBoxBe()) {
            const tablesIds = tables.map((table) => table.id);
            return this.pos.models["restaurant.table"].some(
                (table) => !tablesIds.includes(table.id)
            );
        }
        return true;
    },
});
