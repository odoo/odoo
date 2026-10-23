import { Record } from "@web/model/relational_model/record";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { FormErrorDialog } from "@web/views/form/form_error_dialog/form_error_dialog";

class StockOrderpointRecord extends Record {
    save(options = {}) {
        return super.save({
            onError: (error) => {
                if (this._errorDialogOpen) {
                    return false;
                }
                this._errorDialogOpen = true;
                this.model.dialog.add(
                    FormErrorDialog,
                    {
                        message: error.data.message,
                        data: error.data,
                        onDiscard: () => this.model.root.leaveEditMode({ discard: true }),
                        onStayHere: () => {},
                    },
                    { onClose: () => (this._errorDialogOpen = false) }
                );
                return false;
            },
            ...options,
        });
    }
}

export class StockOrderpointListModel extends RelationalModel {
    static Record = StockOrderpointRecord;
}
