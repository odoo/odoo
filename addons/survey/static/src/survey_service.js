import { registry } from "@web/core/registry";

const surveyService = {
    start() {
        let options = {};
        const optionsData = document.querySelector("form.o_survey-fill-form")?.dataset;
        if (optionsData) {
            options = {
                scoringType: optionsData.scoringType,
                answerToken: optionsData.answerToken,
                surveyToken: optionsData.surveyToken,
                usersCanGoBack: !!optionsData.usersCanGoBack,
                sessionInProgress: !!optionsData.sessionInProgress,
                isStartScreen: !!optionsData.isStartScreen,
                readonly: !!optionsData.readonly,
                hasAnswered: !!optionsData.hasAnswered,
                isPageDescription: !!optionsData.isPageDescription,
                questionsLayout: optionsData.questionsLayout,
                triggeredQuestionsByAnswer: JSON.parse(optionsData.triggeredQuestionsByAnswer),
                triggeringAnswersByQuestion: JSON.parse(optionsData.triggeringAnswersByQuestion),
                selectedAnswers: JSON.parse(optionsData.selectedAnswers),
                refreshBackground: !!optionsData.refreshBackground,
            };
        }
        return {
            options,
        };
    },
};

registry.category("services").add("survey", surveyService);
