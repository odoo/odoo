import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

class Many2XSpreadsheetAutocomplete extends Many2XAutocomplete {
    setup() {
        super.setup();
        const actionService = useService("action");
        // Overwrite the "Create and edit" function to create a new spreadsheet
        // and open it.
        // The standard behavior opens a dialog with the form view
        this.openMany2X = async ({ context }) => {
            const action = await this.orm.call(
                this.props.resModel,
                "action_open_new_spreadsheet",
                [],
                { context }
            );
            this.props.update([{ id: action.params.spreadsheet_id }]);
            await this.env.model.root.save();
            await actionService.doAction(action);
        };
    }
}

class Many2OneSpreadsheetField extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        // replace the Many2XAutocomplete component by our custom autocomplete
        Many2XAutocomplete: Many2XSpreadsheetAutocomplete,
    };
}

registry.category("fields").add("many2one_spreadsheet", {
    ...many2OneField,
    component: Many2OneSpreadsheetField,
});
