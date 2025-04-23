import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { EventBus, useSubEnv } from "@odoo/owl";

export class SurveyInviteController extends formView.Controller {
    static props = {
        ...formView.Controller.props,
        fullComposerBus: { type: EventBus, optional: true },
    };
    static defaultProps = { fullComposerBus: new EventBus() };
    setup() {
        super.setup();
        useSubEnv({
            fullComposerBus: this.props.fullComposerBus,
        });
    }
}

registry.category("views").add("survey_invite_form", {
    ...formView,
    Controller: SurveyInviteController,
});
