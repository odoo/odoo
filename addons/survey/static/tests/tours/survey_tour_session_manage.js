odoo.define('survey.test_survey_session_manage_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');
var surveySessionTools = require('survey.session_tour_tools');

/**
 * Since the chart is rendered using SVG, we can't use jQuery triggers to check if everything
 * is correctly rendered.
 * This helper method returns the chart data (Chartjs framework specific) in the following structure:
 * [{ value, backgroundColor, labelColor }]
 */
var getChartData = function () {
    var chartData = [];
    var rootWidget = odoo.__DEBUG__.services['root.widget'];
    var surveyManagePublicWidget = rootWidget.publicWidgets.find(function (widget) {
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

var nextScreen = function () {
    var e = $.Event('keydown');
    e.keyCode = 39; // arrow-right
    $(document).trigger(e);
};

var previousScreen = function () {
    var e = $.Event('keydown');
    e.keyCode = 37; // arrow-left
    $(document).trigger(e);
};

var REGULAR_ANSWER_COLOR = '#212529';
var CORRECT_ANSWER_COLOR = '#2CBB70';
var WRONG_ANSWER_COLOR = '#D9534F';

/**
 * A 'regular' answer is an answer that is nor correct, nor incorrect.
 * The check is based on the specific opacity (0.8) and color of those answers.
 */
var isRegularAnswer = function (answer) {
    return answer.backgroundColor.includes('0.8') &&
        answer.labelColor === REGULAR_ANSWER_COLOR;
};

/**
 * The check is based on the specific opacity (0.8) and color of correct answers.
 */
var isCorrectAnswer = function (answer) {
    return answer.backgroundColor.includes('0.8') &&
        answer.labelColor === CORRECT_ANSWER_COLOR;
};

/**
 * The check is based on the specific opacity (0.2) and color of incorrect answers.
 */
var isIncorrectAnswer = function (answer) {
    return answer.backgroundColor.includes('0.2') &&
        answer.labelColor === WRONG_ANSWER_COLOR;
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
tour.register('test_survey_session_manage_tour', {
    url: "/web",
    test: true,
}, [].concat(surveySessionTools.accessSurveySteps, [{
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
    run: function () {
        var chartData = getChartData();
        if (chartData.length !== 3) {
            console.error('Chart data should contain 3 records!');
            return;
        }

        var firstAnswerData = chartData[0];
        if (firstAnswerData.value !== 2 || !isRegularAnswer(firstAnswerData)) {
            console.error('First answer should be picked by 2 users!');
            return;
        }

        var secondAnswerData = chartData[1];
        if (secondAnswerData.value !== 1 || !isRegularAnswer(secondAnswerData)) {
            console.error('Second answer should be picked by 1 user!');
            return;
        }

        var thirdAnswerData = chartData[2];
        if (thirdAnswerData.value !== 0 || !isRegularAnswer(thirdAnswerData)) {
            console.error('Third answer should be picked by no users!');
            return;
        }

        nextScreen();
    }
}, {
    trigger: 'h1:contains("Scored Simple Choice")',
    run: function () {
        var chartData = getChartData();
        if (chartData.length !== 4) {
            console.error('Chart data should contain 4 records!');
            return;
        }

        for (var i = 0; i < chartData.length; i++) {
            if (chartData[i].value !== 0) {
                console.error(
                    'Chart data should all be 0 because "next screen" that shows ' +
                    'answers values is not triggered yet!');
                return;
            }
        }

        nextScreen();
        chartData = getChartData();

        var firstAnswerData = chartData[0];
        if (firstAnswerData.value !== 1 || !isRegularAnswer(firstAnswerData)) {
            console.error(
                'First answer should be picked by 1 user and its correctness should not be shown yet!'
            );
            return;
        }

        var secondAnswerData = chartData[1];
        if (secondAnswerData.value !== 1 || !isRegularAnswer(secondAnswerData)) {
            console.error(
                'Second answer should be picked by 1 user and its correctness should not be shown yet!'
            );
            return;
        }

        var thirdAnswerData = chartData[2];
        if (thirdAnswerData.value !== 1 || !isRegularAnswer(thirdAnswerData)) {
            console.error(
                'Third answer should be picked by 1 user and its correctness should not be shown yet!'
            );
            return;
        }

        var fourthAnswerData = chartData[3];
        if (fourthAnswerData.value !== 0 || !isRegularAnswer(fourthAnswerData)) {
            console.error(
                'Fourth answer should be picked by no users and its correctness should not be shown yet!'
            );
            return;
        }

        nextScreen();
        chartData = getChartData();

        firstAnswerData = chartData[0];
        if (firstAnswerData.value !== 1 || !isCorrectAnswer(firstAnswerData)) {
            console.error(
                'First answer should be picked by 1 user and it should be correct!'
            );
            return;
        }

        secondAnswerData = chartData[1];
        if (secondAnswerData.value !== 1 || !isIncorrectAnswer(secondAnswerData)) {
            console.error(
                'Second answer should be picked by 1 user and it should be incorrect!'
            );
            return;
        }

        thirdAnswerData = chartData[2];
        if (thirdAnswerData.value !== 1 || !isIncorrectAnswer(thirdAnswerData)) {
            console.error(
                'Third answer should be picked by 1 user and it should be incorrect!'
            );
            return;
        }

        fourthAnswerData = chartData[3];
        if (fourthAnswerData.value !== 0 || !isIncorrectAnswer(fourthAnswerData)) {
            console.error(
                'Fourth answer should be picked by no users and it should be incorrect!'
            );
            return;
        }

        nextScreen();
        nextScreen();
    }
}, {
    trigger: 'h1:contains("Timed Scored Multiple Choice")',
    run: function () {
        var chartData = getChartData();
        if (chartData.length !== 3) {
            console.error('Chart data should contain 4 records!');
            return;
        }

        for (var i = 0; i < chartData.length; i++) {
            if (chartData[i].value !== 0) {
                console.error(
                    'Chart data should all be 0 because "next screen" that shows ' +
                    'answers values is not triggered yet!');
                return;
            }
        }

        // after 1 second, results are displayed automatically because question timer runs out
        // we add 1 extra second because of the way the timer works:
        // it only triggers the time_up event 1 second AFTER the delay is passed
        setTimeout(function () {
            chartData = getChartData();
            var firstAnswerData = chartData[0];
            if (firstAnswerData.value !== 2 || !isRegularAnswer(firstAnswerData)) {
                console.error(
                    'First answer should be picked by 2 users and its correctness should not be shown yet!'
                );
                return;
            }

            var secondAnswerData = chartData[1];
            if (secondAnswerData.value !== 2 || !isRegularAnswer(secondAnswerData)) {
                console.error(
                    'Second answer should be picked by 2 users and its correctness should not be shown yet!'
                );
                return;
            }

            var thirdAnswerData = chartData[2];
            if (thirdAnswerData.value !== 1 || !isRegularAnswer(thirdAnswerData)) {
                console.error(
                    'Third answer should be picked by 1 user and its correctness should not be shown yet!'
                );
                return;
            }

            nextScreen();
            chartData = getChartData();

            firstAnswerData = chartData[0];
            if (firstAnswerData.value !== 2 || !isCorrectAnswer(firstAnswerData)) {
                console.error(
                    'First answer should be picked by 2 users and it should be correct!'
                );
                return;
            }

            secondAnswerData = chartData[1];
            if (secondAnswerData.value !== 2 || !isCorrectAnswer(secondAnswerData)) {
                console.error(
                    'Second answer should be picked by 2 users and it should be correct!'
                );
                return;
            }

            thirdAnswerData = chartData[2];
            if (thirdAnswerData.value !== 1 || !isIncorrectAnswer(thirdAnswerData)) {
                console.error(
                    'Third answer should be picked by 1 user and it should be incorrect!'
                );
                return;
            }

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
        var chartData = getChartData();

        var firstAnswerData = chartData[0];
        if (firstAnswerData.value !== 2 || !isCorrectAnswer(firstAnswerData)) {
            console.error(
                'First answer should be picked by 2 users and it should be correct!'
            );
            return;
        }

        var secondAnswerData = chartData[1];
        if (secondAnswerData.value !== 2 || !isCorrectAnswer(secondAnswerData)) {
            console.error(
                'Second answer should be picked by 2 users and it should be correct!'
            );
            return;
        }

        var thirdAnswerData = chartData[2];
        if (thirdAnswerData.value !== 1 || !isIncorrectAnswer(thirdAnswerData)) {
            console.error(
                'Third answer should be picked by 1 user and it should be incorrect!'
            );
            return;
        }

        previousScreen();
        chartData = getChartData();

        firstAnswerData = chartData[0];
        if (firstAnswerData.value !== 2 || !isRegularAnswer(firstAnswerData)) {
            console.error(
                'First answer should be picked by 2 users and its correctness should not be shown!'
            );
            return;
        }

        secondAnswerData = chartData[1];
        if (secondAnswerData.value !== 2 || !isRegularAnswer(secondAnswerData)) {
            console.error(
                'Second answer should be picked by 2 users and its correctness should not be shown!'
            );
            return;
        }

        thirdAnswerData = chartData[2];
        if (thirdAnswerData.value !== 1 || !isRegularAnswer(thirdAnswerData)) {
            console.error(
                'Third answer should be picked by 1 user and its correctness should not be shown!'
            );
            return;
        }

        previousScreen();
        chartData = getChartData();

        for (var i = 0; i < chartData.length; i++) {
            if (chartData[i].value !== 0) {
                console.error(
                    'Chart data should all be 0 because "next screen" that shows ' +
                    'answers values is not triggered yet!');
                return;
            }
        }

        // Now we go forward to the "Final Leaderboard" again (3 times)
        for (i = 0; i < 3; i++) {
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
}]));

});
