import { useSubEnv } from "@web/owl2/utils";
import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { formControllerProps } from "@web/views/form/form_controller";
import { EventBus, props, t } from "@odoo/owl";

const defaultFullComposerBus = new EventBus();

export class SurveyInviteController extends formView.Controller {
    props = props({
        ...formControllerProps,
        fullComposerBus: t.instanceOf(EventBus).optional(defaultFullComposerBus),
    });
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
