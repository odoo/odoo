import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class SelectSurveyOption extends BaseOptionComponent {
    static id = "select_survey_option";
    static template = "mass_mailing.SelectSurveyOption";
}

export class SelectSurveyAction extends BuilderAction {
    static id = "selectSurveyAction";

    getValue({ editingElement: el }) {
        if (!el.dataset.surveyId) {
            return;
        }
        const title = el.dataset.surveyTitle;
        const href = el.querySelector(".o_snippet_take_survey_btn")?.getAttribute("href") || "";
        return JSON.stringify({
            id: parseInt(el.dataset.surveyId),
            display_name: title,
            name: title,
            title,
            access_token: href.split("/survey/start/")[1],
        });
    }

    async apply({ editingElement: el, value }) {
        value = JSON.parse(value);
        el.dataset.surveyId = value.id;
        el.dataset.surveyTitle = value.title;
        const surveyButton = el.querySelector(".o_snippet_take_survey_btn");
        surveyButton.href = "/survey/start/" + value.access_token;
    }
}

export class SelectSurveyOptionPlugin extends Plugin {
    static id = "selectSurveyOptionPlugin";

    resources = {
        builder_actions: {
            SelectSurveyAction,
        },
    };
}

registry.category("mass_mailing-options").add(SelectSurveyOption.id, SelectSurveyOption);
registry
    .category("mass_mailing-plugins")
    .add(SelectSurveyOptionPlugin.id, SelectSurveyOptionPlugin);
