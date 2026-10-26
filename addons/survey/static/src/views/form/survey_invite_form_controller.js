import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { formControllerProps } from "@web/views/form/form_controller";
import { EventBus, providePlugins, useProps, t } from "@odoo/owl";
import { FullComposerBusPlugin } from "@mail/core/web/full_composer_bus_plugin";

const defaultFullComposerBus = new EventBus();

export class SurveyInviteController extends formView.Controller {
    props = useProps({
        ...formControllerProps,
        fullComposerBus: t.instanceOf(EventBus).optional(defaultFullComposerBus),
    });
    setup() {
        super.setup();
        providePlugins([FullComposerBusPlugin], { bus: this.props.fullComposerBus });
    }
}

registry.category("views").add("survey_invite_form", {
    ...formView,
    Controller: SurveyInviteController,
});
