import { Interaction } from "@web/public/interaction";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

export class SurveyQuickAccess extends Interaction {
    static selector = ".o_survey_quick_access";

    dynamicContent = {
        _document: { "t-on-keypress": this.onKeyPress },
        "button[type='submit']": { 
            "t-on-click.prevent": this.submitCode,
            "t-att-class": () => ({ "d-none": this.isLaunchShown })
        },
        "#session_code": { "t-on-input": this.onSessionCodeInput },
        ".o_survey_launch_session": { 
            "t-on-click": this.onLaunchSessionClick,
            "t-att-class": () => ({ "d-none": !this.isLaunchShown }),
        },
        ".o_survey_session_error_not_launched": { "t-att-class": () => ({ "d-none": this.errorCode !== "not_launched" }) },
        ".o_survey_session_error_invalid_code": { "t-att-class": () => ({ "d-none": this.errorCode !== "invalid_code" }) },

    };

    async onLaunchSessionClick() {
        const sessionResult = await this.waitFor(this.services.orm.call(
            "survey.survey",
            "action_start_session",
            [[parseInt(this.el.querySelector(".o_survey_launch_session").dataset.surveyId)]]
        ));
        window.location = sessionResult.url;
    }

    onSessionCodeInput() {
        this.errorCode = "";
        this.isLaunchShown = false;
    }

    onKeyPress(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            this.submitCode();
        }
    }

    async submitCode() {
        this.errorCode = "";
        const sessionCodeInputVal = encodeURIComponent(this.el.querySelector("input#session_code").value.trim());
        if (!sessionCodeInputVal) {
            this.errorCode = "invalid_code";
            return;
        }
        const response = await this.waitFor(rpc(`/survey/check_session_code/${sessionCodeInputVal}`));
        this.protectSyncAfterAsync(() => {
            if (response.survey_url) {
                window.location = response.survey_url;
            } else {
                if (response.error && response.error === "survey_session_not_launched") {
                    this.errorCode = "not_launched";
                    if ("survey_id" in response) {
                        this.isLaunchShown = true;
                        this.el.querySelector(".o_survey_launch_session").dataset.surveyId = response.survey_id;
                    }
                } else {
                    this.errorCode = "invalid_code";
                }
            }
        })();
    }
}

registry
    .category("public.interactions")
    .add("survey.survey_quick_access", SurveyQuickAccess);
