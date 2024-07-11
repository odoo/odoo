/** @odoo-module **/

import { registry } from "@web/core/registry";
import { zip } from "@web/core/utils/arrays";
import { TourError } from "@web_tour/tour_service/tour_utils";
import { accessSurveysteps } from "./survey_tour_session_tools";

let rootWidget = null;

/**
 * Since the chart is rendered using SVG, we can't use jQuery triggers to check if everything
 * is correctly rendered.
 * This helper method returns the chart data (Chartjs framework specific) in the following structure:
 * [{ value, backgroundColor, labelColor }]
 */
const getChartData = () => {
    const chartData = [];
    const surveyManagePublicWidget = rootWidget.publicWidgets.find((widget) => {
        return widget.$el.hasClass('o_survey_session_manage');
    });

    if (!surveyManagePublicWidget) {
        return chartData;
    }

    surveyManagePublicWidget.resultsChart.chart.data.datasets[0].data.forEach((value, index)=> {
        chartData.push({
            value: value,
            backgroundColor: surveyManagePublicWidget.resultsChart._getBackgroundColor({dataIndex: index}),
            labelColor: surveyManagePublicWidget.resultsChart._getLabelColor({dataIndex: index}),
        });
    });

    return chartData;
};

const nextScreen = () => {
    const e = $.Event('keydown');
    e.key = "ArrowRight";
    $(document).trigger(e);
};

const previousScreen = () => {
    const e = $.Event('keydown');
    e.key = "ArrowLeft";
    $(document).trigger(e);
};

const REGULAR_ANSWER_COLOR = '#212529';
const CORRECT_ANSWER_COLOR = '#2CBB70';
const WRONG_ANSWER_COLOR = '#D9534F';

const INDEX_TO_ORDINAL = {
    0: 'First',
    1: 'Second',
    2: 'Third',
    3: 'Fourth',
};

/**
 * Check answer appearance (opacity and color).
 *
 * @param {string} answerLabel
 * @param {{backgroundColor: string, labelColor: string, value?: number}} shownAnswer
 * @param {"correct"|"incorrect"|"regular"} expectedAnswerType
 */
const checkAnswerAppearance = (answerLabel, shownAnswer, expectedAnswerType) => {
    if (expectedAnswerType === 'correct') {
        if (!shownAnswer.backgroundColor.includes('0.8') || shownAnswer.labelColor !== CORRECT_ANSWER_COLOR) {
            throw new TourError(`${answerLabel} should be shown as "correct"!`);
        }
    } else if (expectedAnswerType === 'incorrect') {
        if (!shownAnswer.backgroundColor.includes('0.2') || shownAnswer.labelColor !== WRONG_ANSWER_COLOR) {
            throw new TourError(`${answerLabel} should be shown as "incorrect"!`);
        }
    } else if (expectedAnswerType === 'regular') {
        if (!shownAnswer.backgroundColor.includes('0.8') || shownAnswer.labelColor !== REGULAR_ANSWER_COLOR) {
            throw new TourError(`${answerLabel} should not be shown as "correct" or "incorrect"!`);
        }
    } else {
        throw new Error(`Unsupported answer type.`);
    }
};

const checkAnswerValue = (answerLabel, shownAnswerValue, expectedAnswerValue) => {
    if (shownAnswerValue !== expectedAnswerValue) {
        throw new TourError(expectedAnswerValue === 0 ?
            `${answerLabel} should not be picked by any user!` :
            `${answerLabel} should be picked by ${expectedAnswerValue} users!`
        );
    }
};

/**
 * Check the answers count, values and appearance.
 *
 * @param {{value: number, backgroundColor: string, color: string}[]} chartData Data returned by `getChartData`.
 * @param {{value: number, type: "correct" | "incorrect" | "regular"}[]} expectedAnswersData
 */
const checkAnswers = (chartData, expectedAnswersData) => {
    checkAnswersCount(chartData, expectedAnswersData.length);

    zip(chartData, expectedAnswersData).forEach(([shownAnswerData, expectedAnswerData], answerIndex) => {
        const answerLabel = `${INDEX_TO_ORDINAL[answerIndex]} answer`;
        checkAnswerValue(answerLabel, shownAnswerData.value, expectedAnswerData.value);
        checkAnswerAppearance(answerLabel, shownAnswerData, expectedAnswerData.type);
    });
};

const checkAnswersAllZeros = (chartData) => {
    if (chartData.find(answerData => answerData !== 0).length) {
        throw new TourError('Chart data should all be 0!');
    }
};

const checkAnswersCount = (chartData, expectedCount) => {
    if (chartData.length !== expectedCount) {
        throw new TourError(`Chart data should contain ${expectedCount} records!`);
    }
};

/**
 * Tour that will test the whole survey session from the host point of view.
 *
 * Break down of the main points:
 * - Open the 'session manager' (the session was already created by a previous tour)
 * - Display the nickname question, and move to the next one (as answers are not displayed)
 * - Check answers are correctly displayed for the 3 'simple' question types (text, date, datetime)
 * - Move to the choice question and check that answers are displayed
 *   (The check is rather complex, see 'getChartData' for details)
 * - If everything is correctly displayed, move to the next question
 * - On the scored choice question, check that the screens are correctly chained:
 *   no results displayed -> results displayed -> correct/incorrect answers -> leaderboard
 * - On the scored + timed multiple choice question, check the same than previous question,
 *   except that the results are supposed to be displayed automatically when the question timer runs out
 * - Test the 'back' behavior and check that screens are reversed correctly
 * - Check that our final leaderboard is correct based on attendees answers
 * - Close the survey session
 */
registry.category("web_tour.tours").add('test_survey_session_manage_tour', {
    url: "/web",
    test: true,
    steps: () => [].concat(accessSurveysteps, [{
    trigger: 'button[name="action_open_session_manager"]',
}, {
    trigger: 'h1:contains("Nickname")',
    isCheck: true // check nickname question is displayed
}, {
    trigger: 'body',
    run: async () => { rootWidget = await odoo.loader.modules.get('root.widget'); }
}, {
    trigger: 'h1',
    run: nextScreen
}, {
    trigger: 'h1:contains("Text Question")',
    isCheck: true // check text question is displayed
}, {
    trigger: '.o_survey_session_progress_small:contains("3 / 3")',
    isCheck: true // check we have 3 answers
}, {
    trigger: '.o_survey_session_text_answer_container:contains("Attendee 1 is the best")',
    isCheck: true // check attendee 1 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("Attendee 2 rulez")',
    isCheck: true // check attendee 2 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("Attendee 3 will crush you")',
    isCheck: true // check attendee 3 answer is displayed
}, {
    trigger: 'h1',
    run: nextScreen
}, {
    trigger: '.o_survey_session_progress_small:contains("2 / 3")',
    isCheck: true // check we have 2 answers
}, {
    trigger: '.o_survey_session_text_answer_container:contains("10/10/2010")',
    isCheck: true // check attendee 1 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("11/11/2011")',
    isCheck: true // check attendee 2 answer is displayed
}, {
    trigger: 'h1',
    run: previousScreen
}, {
    trigger: 'h1:contains("Text Question")',
    isCheck: true // check text question is displayed
}, {
    trigger: '.o_survey_session_progress_small:contains("3 / 3")',
    isCheck: true // check we have 3 answers
}, {
    trigger: '.o_survey_session_text_answer_container:contains("Attendee 1 is the best")',
    isCheck: true // check attendee 1 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("Attendee 2 rulez")',
    isCheck: true // check attendee 2 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("Attendee 3 will crush you")',
    isCheck: true // check attendee 3 answer is displayed
}, {
    trigger: 'h1',
    run: nextScreen
}, {
    trigger: '.o_survey_session_progress_small:contains("2 / 3")',
    isCheck: true // check we have 2 answers
}, {
    trigger: '.o_survey_session_text_answer_container:contains("10/10/2010")',
    isCheck: true // check attendee 1 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("11/11/2011")',
    isCheck: true // check attendee 2 answer is displayed
}, {
    trigger: 'h1',
    run: nextScreen
}, {
    trigger: '.o_survey_session_progress_small:contains("2 / 3")',
    isCheck: true // check we have 2 answers
}, {
    trigger: '.o_survey_session_text_answer_container:contains("10/10/2010 10:00:00")',
    isCheck: true // check attendee 2 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("11/11/2011 15:55:55")',
    isCheck: true // check attendee 3 answer is displayed
}, {
    trigger: 'h1',
    run: nextScreen
}, {
    trigger: 'h1:contains("Regular Simple Choice")',
    // Wait for answers' data to be fetched (see commit message).
    extra_trigger: '.o_survey_session_progress_small[style*="width: 100%"]',
    run: () => {
        checkAnswers(getChartData(), [
            {value: 2, type: "regular"},
            {value: 1, type: "regular"},
            {value: 0, type: "regular"},
        ]);
        nextScreen();
    }
}, {
    trigger: 'h1:contains("Scored Simple Choice")',
    run: () => {
        const chartData = getChartData();
        checkAnswersCount(chartData, 4);
        checkAnswersAllZeros(chartData);

        nextScreen();
    }
}, {
    trigger: 'h1:contains("Scored Simple Choice")',
    // Wait for progressbar to be updated ("late" enough DOM change after onNext() is triggered).
    extra_trigger: '.o_survey_session_progress_small[style*="width: 100%"]',
    run: () => {
        checkAnswers(getChartData(), [
            {value: 1, type: "regular"},
            {value: 1, type: "regular"},
            {value: 1, type: "regular"},
            {value: 0, type: "regular"},
        ]);
        nextScreen();
    }
}, {
    trigger: 'h1:contains("Scored Simple Choice")',
    // Wait for Button to be updated ("late" enough DOM change after onNext() is triggered).
    extra_trigger: '.o_survey_session_navigation_next_label:contains("Show Leaderboard")',
    run: () => {
        checkAnswers(getChartData(), [
            {value: 1, type: "correct"},
            {value: 1, type: "incorrect"},
            {value: 1, type: "incorrect"},
            {value: 0, type: "incorrect"},
        ]);
        nextScreen();
        nextScreen();
    }
}, {
    trigger: 'h1:contains("Timed Scored Multiple Choice")',
    run: ()=> {
        const chartData = getChartData();
        checkAnswersCount(chartData, 3);
        checkAnswersAllZeros(chartData);

        // after 1 second, results are displayed automatically because question timer runs out
        // we add 1 extra second because of the way the timer works:
        // it only triggers the time_up event 1 second AFTER the delay is passed
        setTimeout(() => {
            checkAnswers(getChartData(), [
                {value: 2, type: "regular"},
                {value: 2, type: "regular"},
                {value: 1, type: "regular"},
            ]);

            nextScreen();
            checkAnswers(getChartData(), [
                {value: 2, type: "correct"},
                {value: 2, type: "correct"},
                {value: 1, type: "incorrect"},
            ]);

            nextScreen();
        }, 2100);
    }
}, {
    trigger: 'h1:contains("Final Leaderboard")',
    isCheck: true // Final Leaderboard is displayed
}, {
    trigger: 'h1',
    run: () => {
        // previous screen testing
        previousScreen();
        checkAnswers(getChartData(), [
            {value: 2, type: "correct"},
            {value: 2, type: "correct"},
            {value: 1, type: "incorrect"},
        ]);

        previousScreen();
        checkAnswers(getChartData(), [
            {value: 2, type: "regular"},
            {value: 2, type: "regular"},
            {value: 1, type: "regular"},
        ]);

        previousScreen();
        checkAnswersAllZeros(getChartData());

        // Now we go forward to the "Final Leaderboard" again (3 times)
        for (let i = 0; i < 3; i++) {
            nextScreen();
        }
    }
}, {
    trigger: 'h1:contains("Final Leaderboard")',
    isCheck: true // Final Leaderboard is displayed
}, {
    trigger: '.o_survey_session_close:has("i.fa-close")'
}, {
    trigger: 'button[name="action_start_session"]',
    isCheck: true // check that we can start another session
}])});
