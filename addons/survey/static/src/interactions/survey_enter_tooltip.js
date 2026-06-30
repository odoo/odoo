import { isMacOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class SurveyEnterTooltip extends Interaction {
    static selector = ".o_survey_form #enter-tooltip";

    dynamicSelectors = {
        ...this.dynamicSelectors,
        _inputs: () => document.querySelectorAll(".o_survey_form .form-control"),
    };

    dynamicContent = {
        _inputs: {
            "t-on-focusin": this.updateEnterButtonText,
            "t-on-focusout": this.updateEnterButtonText,
        },
        _root: {
            "t-out": () => this.enterTooltipText,
        },
    };

    setup() {
        this.isMac = isMacOS();
        this.defaultText = _t("or press Enter");
        this.otherText = isMacOS() ? _t("or press ⌘+Enter") : _t("or press CTRL+Enter");
        this.enterTooltipText = this.defaultText;
        const { questionsLayout } =
            document.querySelector("form.o_survey-fill-form")?.dataset || {};
        this.surveyQuestionsLayout = questionsLayout;
    }

    start() {
        const activeEl = document.activeElement;
        this.updateTooltip(
            document.hasFocus() &&
                activeEl.tagName.toLowerCase() === "textarea" &&
                activeEl.classList.contains("form-control")
        );
        this.updateContent();
    }

    updateEnterButtonText(ev) {
        const targetEl = ev.target;
        const isTextbox = ev.type === "focusin" && targetEl.tagName.toLowerCase() === "textarea";
        this.updateTooltip(isTextbox);
    }

    updateTooltip(isTextbox) {
        this.enterTooltipText =
            isTextbox || ["one_page", "page_per_section"].includes(this.surveyQuestionsLayout)
                ? this.otherText
                : this.defaultText;
    }
}

registry.category("public.interactions").add("survey.SurveyEnterTooltip", SurveyEnterTooltip);
