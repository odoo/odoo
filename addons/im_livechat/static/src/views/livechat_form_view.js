import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { LivechatSessionFormRenderer } from "./livechat_form_renderer";

export const LivechatSesionFormView = {
    ...formView,
    Renderer: LivechatSessionFormRenderer,
    display: { controlPanel: false },
};

registry.category("views").add("livechat_session_form", LivechatSesionFormView);
