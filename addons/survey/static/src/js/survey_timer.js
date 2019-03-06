odoo.define('survey.timer', function (require) {
'use strict';

require('web.dom_ready');

if (!$('.js_survey_timer').length) {
    return Promise.reject("DOM doesn't contain '.js_survey_timer'");
}

var $parent = $('.js_survey_timer');
var timeLimitMinutes = parseInt($parent.data('time_limit_minutes'));

if (timeLimitMinutes <= 0) {
    return Promise.reject("Timer is not positive");
}

var countDownDate = moment.utc($parent.data('timer')).add(timeLimitMinutes, 'minutes');

if (countDownDate.diff(moment.utc(), 'seconds') < 0) {
    return Promise.reject("Timer is already finished");
}

var formatTime = function (time) {
    return time > 9 ? time : '0' + time;
};

var $timer = $parent.find('.timer');
var interval = null;
var updateTimer = function () {
    var timeLeft = countDownDate.diff(moment.utc(), 'seconds');

    if (timeLeft >= 0) {
        var timeLeftMinutes = parseInt(timeLeft / 60);
        var timeLeftSeconds = timeLeft - (timeLeftMinutes * 60);
        $timer.html(formatTime(timeLeftMinutes) + ':' + formatTime(timeLeftSeconds));
    } else {
        clearInterval(interval);
        $('.js_surveyform').submit();
    }
};

updateTimer();
interval = setInterval(updateTimer, 1000);

});
