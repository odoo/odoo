import { Plugin } from "@html_editor/plugin";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";

export class TakeSurveySnippetPlugin extends Plugin {
    static id = "mass_mailing.TakeSurveySnippetPlugin";
    static dependencies = ["history"];
    resources = {
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    onSnippetDropped({ snippetEl }) {
        if (
            !snippetEl.matches(".o_snippet_take_survey") ||
            registry.category("mass_mailing-options").contains("select_survey_option")
        ) {
            return;
        }
        const removeSnippet = () => {
            snippetEl.remove();
            this.dependencies.history.commit();
        };
        if (!user.isSystem) {
            this.services.notification.add(
                _t(
                    "The Surveys app is required to use this block. Please ask your administrator to install it."
                ),
                { type: "warning" }
            );
            removeSnippet();
            return;
        }
        this.services.dialog.add(ConfirmationDialog, {
            title: _t("Install Survey"),
            body: _t("This block requires the Surveys app. Do you want to install it?"),
            confirm: () => this.installSurvey(),
            cancel: removeSnippet,
        });
    }

    async installSurvey() {
        if (!(await this.config.record.save())) {
            return;
        }
        this.services.ui.block();
        try {
            const [moduleId] = await this.services.orm.search("ir.module.module", [
                ["name", "=", "mass_mailing_survey"],
            ]);
            const action = await this.services.orm.call(
                "ir.module.module",
                "button_immediate_install",
                [[moduleId]]
            );
            await this.services.action.doAction(action);
        } finally {
            this.services.ui.unblock();
        }
    }
}

registry.category("mass_mailing-plugins").add(TakeSurveySnippetPlugin.id, TakeSurveySnippetPlugin);
