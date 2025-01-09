import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { TodoFormController } from "./todo_form_controller";
<<<<<<< 18.0
import { TodoFormControlPanel } from "./todo_form_control_panel";
||||||| 1fb35add8090b5fc9e706aad67f6bb38432273e0
=======
>>>>>>> da59bf1857979ad7dae5008bc3c832ae6619a517
import { TodoFormRenderer } from "./todo_form_renderer";

export const todoFormView = {
    ...formView,
    Controller: TodoFormController,
<<<<<<< 18.0
    ControlPanel: TodoFormControlPanel,
||||||| 1fb35add8090b5fc9e706aad67f6bb38432273e0
=======
>>>>>>> da59bf1857979ad7dae5008bc3c832ae6619a517
    Renderer: TodoFormRenderer,
};

registry.category("views").add("todo_form", todoFormView);
