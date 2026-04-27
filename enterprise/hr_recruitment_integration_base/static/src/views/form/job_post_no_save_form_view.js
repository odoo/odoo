import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { JobPostNoSaveFormController } from "./job_post_no_save_controller";

registry.category("views").add("job_post_no_save_form", {
    ...formView,
    Controller: JobPostNoSaveFormController,
});
