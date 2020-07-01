odoo.define('website_event_track_quiz.quiz.finish', function (require) {
'use strict';

var Dialog = require('web.Dialog');

/**
 * This modal is used when the user finishes the quiz.
 * It handles the animation of karma gain and leveling up by animating
 * the progress bar and the text.
 */
var QuizFinishModal = Dialog.extend({
    template: 'quiz.finish',

    init: function (parent, options) {
        this.quiz = options.quiz;
        this.hasNext = options.hasNext;
        this.userId = options.userId;
        this.progressBar = options.progressBar;
        this.karmaMode = options.karmaMode;
        options = _.defaults(options || {}, {
            size: 'medium',
            dialogClass: 'd-flex p-0',
            $parentNode: parent.$el,
            technical: false,
            renderHeader: false,
            renderFooter: false
        });
        this._super.apply(this, arguments);
    },

    start: function () {
        var self = this;
        this._super.apply(this, arguments).then(function () {
            self.$modal.addClass('o_quiz_quiz_modal pt-5');
            self.$modal.find('.modal-dialog').addClass('mt-5');
            self.$modal.find('.modal-content').addClass('shadow-lg');
        });
    },

});

return QuizFinishModal;

});
