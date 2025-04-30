import { onMounted } from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class LotAutoComplete extends AutoComplete {
    setup() {
        super.setup();
        onMounted(() => {
            this.onInputClick();
        });
    }
}
