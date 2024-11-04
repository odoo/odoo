import { onMounted } from "@odoo/owl";
import { FormController } from "@web/views/form/form_controller";

export class TodoConversionFormController extends FormController {
    /**
     * Allows to autofocus the first element of the conversion form
     *
     * @override
     * @private
     */
    setup() {
        super.setup();
        onMounted(() => {
            const firstConversionInput = document.querySelector('div.o_todo_conversion_form_view input');
            firstConversionInput.focus();
        });
    }
}
