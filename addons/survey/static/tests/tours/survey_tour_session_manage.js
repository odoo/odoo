/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TourError } from "@web_tour/tour_service/tour_utils";
import { zip } from "@web/core/utils/arrays";

import surveySessionTools from "survey.session_tour_tools";

/**
 * Since the chart is rendered using SVG, we can't use jQuery triggers to check if everything
 * is correctly rendered.
 * This helper method returns the chart data (Chartjs framework specific) in the following structure:
 * [{ value, backgroundColor, labelColor }]
 */
const getChartData = function () {
    const chartData = [];
    const rootWidget = odoo.__DEBUG__.services['root.widget'];
    const surveyManagePublicWidget = rootWidget.publicWidgets.find(function (widget) {
        return widget.$el.hasClass('o_survey_session_manage');
    });

    if (!surveyManagePublicWidget) {
        return chartData;
    }

    surveyManagePublicWidget.resultsChart.chart.data.datasets[0].data.forEach(function (value, index) {
        chartData.push({
            value: value,
            backgroundColor: surveyManagePublicWidget.resultsChart._getBackgroundColor({dataIndex: index}),
            labelColor: surveyManagePublicWidget.resultsChart._getLabelColor({dataIndex: index}),
        });
    });

    return chartData;
};

const nextScreen = function () {
    const e = $.Event('keydown');
    e.keyCode = 39; // arrow-right
    $(document).trigger(e);
};

const previousScreen = function () {
    const e = $.Event('keydown');
    e.keyCode = 37; // arrow-left
    $(document).trigger(e);
};

const REGULAR_ANSWER_COLOR = '#212529';
const CORRECT_ANSWER_COLOR = '#2CBB70';
const WRONG_ANSWER_COLOR = '#D9534F';

/**
 * A 'regular' answer is an answer that is nor correct, nor incorrect.
 * The check is based on the specific opacity (0.8) and color of those answers.
 */
const isRegularAnswer = function (answer) {
    return answer.backgroundColor.includes('0.8') &&
        answer.labelColor === REGULAR_ANSWER_COLOR;
};

/**
 * The check is based on the specific opacity (0.8) and color of correct answers.
 */
const isCorrectAnswer = function (answer) {
    return answer.backgroundColor.includes('0.8') &&
        answer.labelColor === CORRECT_ANSWER_COLOR;
};

/**
 * The check is based on the specific opacity (0.2) and color of incorrect answers.
 */
const isIncorrectAnswer = function (answer) {
    return answer.backgroundColor.includes('0.2') &&
        answer.labelColor === WRONG_ANSWER_COLOR;
};

const _checkAnswersCount = function (chartData, expectedCount) {
    if (chartData.length !== expectedCount) {
        throw new TourError(`Chart data should contain ${expectedCount} records!`);
    }
};

const _checkAllZeros = function (chartData) {
    if (chartData.find(answerData => answerData !== 0).length) {
        throw new TourError('Chart data should all be 0!');
    }
};

const _IS_ASPECT_ANSWER_DATA = {
    "correct": [isCorrectAnswer, 'should be shown as "correct"!'],
    "incorrect": [isIncorrectAnswer, 'should be shown as "incorrect"!'],
    "regular": [isRegularAnswer, 'should not be shown as "correct" or "incorrect"!'],
    "regularScored": [isRegularAnswer, "correctness shouldn't be shown!"],
};
const _INDEX_TO_LABEL = {
    0: 'First',
    1: 'Second',
    2: 'Third',
    3: 'Fourth',
};

/**
 * Check the answers count and aspect.
 *
 * @param {object} chartData Object returned by `getChartData`.
 * @param {{value: number, aspect: "correct" | "incorrect" | "regular" | "regularScored"}[]} expectedAnswersData with:
 *  `value`: expected answers count (number of user inputs)
 *  `aspect`: Appearance of the answers count. Use `regularScored` for scored question
 *    (when the correctness should not be shown) to improve the error message
 */
const checkAnswers = function (chartData, expectedAnswersData) {
    _checkAnswersCount(chartData, expectedAnswersData.length);

    zip(chartData, expectedAnswersData).forEach(([actual, expected], index) => {
        const [isAspectAnswer, aspectErrorMessage] = _IS_ASPECT_ANSWER_DATA[expected.aspect];
        const questionLabel = _INDEX_TO_LABEL[index];
        if (!isAspectAnswer(actual)) {
            throw new Error(`${questionLabel} answer ${aspectErrorMessage}!`);
        }
        if (actual.value !== expected.value) {
            throw new Error(expected.value ?
                `${questionLabel} answer should be picked by ${expected.value} users!`:
                `${questionLabel} answer should not be picked by any user!`
            );
        }
    });
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
    steps: [].concat(surveySessionTools.accessSurveySteps, [{
    trigger: 'button[name="action_open_session_manager"]',
}, {
    trigger: 'h1:contains("Nickname")',
    run: function () {} // check nickname question is displayed
}, {
    trigger: 'h1',
    run: nextScreen
}, {
    trigger: 'h1:contains("Text Question")',
    run: function () {} // check text question is displayed
}, {
    trigger: '.o_survey_session_progress_small:contains("3 / 3")',
    run: function () {} // check we have 3 answers
}, {
    trigger: '.o_survey_session_text_answer_container:contains("Attendee 1 is the best")',
    run: function () {} // check attendee 1 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("Attendee 2 rulez")',
    run: function () {} // check attendee 2 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("Attendee 3 will crush you")',
    run: function () {} // check attendee 3 answer is displayed
}, {
    trigger: 'h1',
    run: nextScreen
}, {
    trigger: '.o_survey_session_progress_small:contains("2 / 3")',
    run: function () {} // check we have 2 answers
}, {
    trigger: '.o_survey_session_text_answer_container:contains("10/10/2010")',
    run: function () {} // check attendee 1 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("11/11/2011")',
    run: function () {} // check attendee 2 answer is displayed
}, {
    trigger: 'h1',
    run: previousScreen
}, {
    trigger: 'h1:contains("Text Question")',
    run: function () {} // check text question is displayed
}, {
    trigger: '.o_survey_session_progress_small:contains("3 / 3")',
    run: function () {} // check we have 3 answers
}, {
    trigger: '.o_survey_session_text_answer_container:contains("Attendee 1 is the best")',
    run: function () {} // check attendee 1 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("Attendee 2 rulez")',
    run: function () {} // check attendee 2 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("Attendee 3 will crush you")',
    run: function () {} // check attendee 3 answer is displayed
}, {
    trigger: 'h1',
    run: nextScreen
}, {
    trigger: '.o_survey_session_progress_small:contains("2 / 3")',
    run: function () {} // check we have 2 answers
}, {
    trigger: '.o_survey_session_text_answer_container:contains("10/10/2010")',
    run: function () {} // check attendee 1 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("11/11/2011")',
    run: function () {} // check attendee 2 answer is displayed
}, {
    trigger: 'h1',
    run: nextScreen
}, {
    trigger: '.o_survey_session_progress_small:contains("2 / 3")',
    run: function () {} // check we have 2 answers
}, {
    trigger: '.o_survey_session_text_answer_container:contains("10/10/2010 10:00:00")',
    run: function () {} // check attendee 2 answer is displayed
}, {
    trigger: '.o_survey_session_text_answer_container:contains("11/11/2011 15:55:55")',
    run: function () {} // check attendee 3 answer is displayed
}, {
    trigger: 'h1',
    run: nextScreen
}, {
    trigger: 'h1:contains("Regular Simple Choice")',
    extra_trigger: '.o_survey_session_progress_small[style*="width: 100%"]',
    run: function () {
        checkAnswers(getChartData(), [
            {value: 2, aspect: "regular"},
            {value: 1, aspect: "regular"},
            {value: 0, aspect: "regular"},
        ]);
        nextScreen();
    }
}, {
    trigger: 'h1:contains("Scored Simple Choice")',
    run: function () {
        const chartData = getChartData();
        _checkAnswersCount(chartData, 4);
        _checkAllZeros(chartData);

        nextScreen();
    }
}, {
    trigger: 'h1:contains("Scored Simple Choice")',
    extra_trigger: '.o_survey_session_navigation_next_label:contains("Show Correct Answer(s)")',
    run: function () {
        checkAnswers(getChartData(), [
            {value: 1, aspect: "regularScored"},
            {value: 1, aspect: "regularScored"},
            {value: 1, aspect: "regularScored"},
            {value: 0, aspect: "regularScored"},
        ]);
        nextScreen();
    }
}, {
    trigger: 'h1:contains("Scored Simple Choice")',
    extra_trigger: '.o_survey_session_navigation_next_label:contains("Show Leaderboard")',
    run: function () {
        checkAnswers(getChartData(), [
            {value: 1, aspect: "correct"},
            {value: 1, aspect: "incorrect"},
            {value: 1, aspect: "incorrect"},
            {value: 0, aspect: "incorrect"},
        ]);
        nextScreen();
        nextScreen();
    }
}, {
    trigger: 'h1:contains("Timed Scored Multiple Choice")',
    run: function () {
        const chartData = getChartData();
        _checkAnswersCount(chartData, 3);
        _checkAllZeros(chartData);

        // after 1 second, results are displayed automatically because question timer runs out
        // we add 1 extra second because of the way the timer works:
        // it only triggers the time_up event 1 second AFTER the delay is passed
        setTimeout(function () {
            checkAnswers(getChartData(), [
                {value: 2, aspect: "regularScored"},
                {value: 2, aspect: "regularScored"},
                {value: 1, aspect: "regularScored"},
            ]);

            nextScreen();
            checkAnswers(getChartData(), [
                {value: 2, aspect: "correct"},
                {value: 2, aspect: "correct"},
                {value: 1, aspect: "incorrect"},
            ]);

            nextScreen();
        }, 2100);
    }
}, {
    trigger: 'h1:contains("Final Leaderboard")',
    run: function () {} // Final Leaderboard is displayed
}, {
    trigger: 'h1',
    run: function () {
        // previous screen testing
        previousScreen();
        checkAnswers(getChartData(), [
            {value: 2, aspect: "correct"},
            {value: 2, aspect: "correct"},
            {value: 1, aspect: "incorrect"},
        ]);

        previousScreen();
        checkAnswers(getChartData(), [
            {value: 2, aspect: "regularScored"},
            {value: 2, aspect: "regularScored"},
            {value: 1, aspect: "regularScored"},
        ]);

        previousScreen();
        _checkAllZeros(getChartData());

        // Now we go forward to the "Final Leaderboard" again (3 times)
        for (let i = 0; i < 3; i++) {
            nextScreen();
        }
    }
}, {
    trigger: 'h1:contains("Final Leaderboard")',
    run: function () {} // Final Leaderboard is displayed
}, {
    trigger: '.o_survey_session_close:has("i.fa-close")'
}, {
    trigger: 'button[name="action_start_session"]',
    run: function () {} // check that we can start another session
}])});
