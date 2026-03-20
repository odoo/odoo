import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from '@web/views/form/form_controller';

export class PropertiesDefinitionFormController extends FormController {
    setup() {
        super.setup();
        this.propertiesState.editable = true;
    }
}

export const PropertiesDefinitionFormView = {
    ...formView,
    Controller: PropertiesDefinitionFormController,
};

registry.category("views").add("properties_definition_form", PropertiesDefinitionFormView);
