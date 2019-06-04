odoo.define('website_slides.quiz_creation', function (require) {
    'use strict';

    var core = require('web.core');
    var publicNotification = require('web.Notification');
    var publicWidget = require('web.public.widget');
    var QWeb = core.qweb;
    var _t = core._t;

    var QuestionDeletionNotification = publicNotification.extend({

        _autoCloseDelay: 5000,

        init: function (parent, params) {
            var self = this;
            this._super(parent, params);
            this.sticky = true;
            this.icon = 'fa-trash';
            this.className += ' bg-danger';
            this.question = params.question;
            this.continueDeletion = true;
            this.buttons = [
                {
                    text: _t('Undo'),
                    primary: true,
                    click: function () {
                        self.continueDeletion = false;
                    }
                }
            ]
        },

        start: function() {
            this._super();
            this._initTimer();
        },

        _initTimer: function() {
            var i = 4;
            var self = this;
            this.timer = setInterval(function () {
                self.$el.find('div.o_notification_content').html(_.str.sprintf(_t("Click Undo to cancel, or in " +
                    "%s seconds the question \"%s\" will be deleted"), i--, self.question.data('title')));
            }, 1000);
            setTimeout(function () {
                self.close();
            }, 5000)
        },

        _onClose: function(ev) {
            console.log('onClose method');
            if (this.continueDeletion) {
                core.bus.trigger('onDeleteQuestion', this.question);
            } else {
                core.bus.trigger('onCancelDeletion', this.question);
            }
            clearInterval(this.timer);
            this._super(ev);
        }
    });

    var NewQuestionWidget = publicWidget.Widget.extend({
        template: 'slide.slide.quiz.new.question',
        events: {
            'click .o_wslides_js_quiz_add_question': '_onAddQuestionClick',
            'click .o_wslides_js_quiz_save': '_onSaveQuestionClick',
            'click .o_wslides_js_quiz_cancel': '_onCancelQuestionClick',
            'click .o_wslides_js_quiz_is_correct': '_onCorrectAnswerClick',
            'click .o_wslides_js_quiz_add_answer': '_onAddAnswerClick',
            'click .o_wslides_js_quiz_delete_answer': '_onDeleteAnswerClick',
        },

        init: function (parent, slideId) {
            this.slideId = slideId;
            this._super(parent);
        },

        start: function () {
            this.renderElement();
        },

        renderElement: function() {
            this._computeQuestionSequence();
            var $newQuestion = this.$el.find('.o_wslides_js_lesson_quiz_new_question');
            $newQuestion.html(QWeb.render('slide.slide.quiz.new.question', {question: {sequence: this.questionSequence}}));
        },

        _computeQuestionSequence: function() {
            if (!this.questionSequence) {
                var elem = this.$el.find('.o_wslides_js_lesson_quiz_question:last .o_wslides_quiz_question_sequence');
                if (elem.length > 0)
                    this.questionSequence = Number(elem.text()) + 1;
                else
                    this.questionSequence = 1;
            }
        },

        _onCorrectAnswerClick: function (ev) {
            ev.preventDefault();
            $(ev.currentTarget).find('input[type=radio]').prop('checked', true);
        },

        _onAddAnswerClick: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            $(ev.currentTarget.parentElement).after(QWeb.render('slide.slide.quiz.answer'));
        },

        _onDeleteAnswerClick: function (ev) {
            ev.preventDefault();
            $(ev.currentTarget.parentElement).remove();
        },

        _formGetValues: function (form) {
            var answers = [];
            var sequence = 1;
            console.log(form);
            form.find('.o_wslides_js_quiz_answers').each(function () {
                var value = $(this).find('input[type=text]').val();
                if (value.trim() !== "") {
                    answers.push({
                        'sequence': sequence++,
                        'text_value': value,
                        'is_correct': $(this).find('input[type=radio]').prop('checked') == true
                    });
                }
            });
            return {
                'sequence': this.questionSequence,
                'question': form.find('.o_wslides_quiz_question input[type=text]').val(),
                'slide_id': this.slideId,
                'answer_ids': answers
            };
        },

        _alertShow: function (form, message) {
            form.find('.o_wslides_js_quiz_create_error').removeClass('d-none');
            form.find('.o_wslides_js_quiz_create_error span:first').html(message);
        },

        _displayCreatedQuestion: function (values) {
            var $lastQuestion = this.$el.find('.o_wslides_js_lesson_quiz_question:last');
            if ($lastQuestion[0])
                $lastQuestion.after(QWeb.render('slide.slide.quiz.question.created', { question:values }));
            else
                this.$el.prepend(QWeb.render('slide.slide.quiz.question.created', { question:values }));
        },

        _displayNewQuizOrNewQuestion: function() {
            if (this.$el.find('.o_wslides_js_lesson_quiz_question').length > 0)
                this._displayAddQuestionButton();
            else
                this._displayAddQuizzButton();
        },

        _displayAddQuizzButton: function () {
            this.$el.find('.o_wslides_js_lesson_quiz_new_question').html(QWeb.render('slide.slide.quiz.new.quiz.button', { slide: { id: this.slideId }}))
        },

        _displayAddQuestionButton: function () {
            this.$el.find('.o_wslides_js_lesson_quiz_new_question').html(QWeb.render('slide.slide.quiz.new.question.button', { slide: { id: this.slideId }}))
        },

        _onAddQuestionClick: function (ev) {
            ev.preventDefault();
            this._createQuestion(ev);
        },

        _onSaveQuestionClick: function (ev) {
            ev.preventDefault();
            this._createQuestion(ev, 'save');
        },

        _onCancelQuestionClick: function(ev) {
            ev.preventDefault();
            this._displayNewQuizOrNewQuestion();
        },

        _validForm: function(form) {
            return form.find('.o_wslides_quiz_question input[type=text]').val().trim() !== "";
        },

        _createQuestion: function (ev, buttonPressed) {
            var self = this;
            var form = $(ev.currentTarget).closest('.o_wslides_js_lesson_quiz_new_question').find('form');
            if (this._validForm(form)) {
                var values = this._formGetValues(form);
                return this._rpc({
                    route: '/slides/slide/quiz/create',
                    params: values
                }).then(function (response) {
                    self._displayCreatedQuestion(response);
                    self.questionSequence++;
                    if (buttonPressed === "save")
                        self._displayNewQuizOrNewQuestion();
                    else
                        self.renderElement();
                }, function (error) {
                    self._alertShow(form, error.message.data.arguments[0]);
                });
            } else {
                this._alertShow(form, _t('Please fill up the question'));
                this.$el.find('.o_wslides_quiz_question input').focus();
            }
        }

    });

    var UpdateQuestionWidget = NewQuestionWidget.extend({
        events: _.extend({}, NewQuestionWidget.prototype.events, {
            'click .o_wslides_js_quiz_update': '_onUpdateClick',
            'click .o_wslides_js_quiz_update_cancel': '_onCancelClick'
        }),

        init: function (parent) {
            this._super(parent);
            console.log(parent);
        },

        start: function () {
            this.renderElement();
        },

        renderElement: function() {
            this.oldHtml = this.$el.html();
            this.$el.html(QWeb.render('slide.slide.quiz.update.question', { question: this._getOldValues() }));
            this.$el.removeClass('completed-disabled');
            this.open = true;
        },

        _isOpen: function() {
            return this.open;
        },

        _getOldValues: function() {
            var answers = [];
            var self = this;
            this.beforeUpdateIDS = [];
            this.$el.find('.o_wslides_quiz_answer').each(function () {
                self.beforeUpdateIDS.push($(this).data('answer-id'));
                answers.push({
                    'id': $(this).data('answer-id'),
                    'text_value': $(this).data('text'),
                    'is_correct': $(this).hasClass('list-group-item-success')
                });
            });
            return {
                'id': this.$el.data('question-id'),
                'sequence': Number(this.$el.find('.o_wslides_quiz_question_sequence').text()),
                'question': this.$el.data('title'),
                'answer_ids': answers
            };
        },

        _getNewValues: function(form) {
            var answerIDS = [];
            var answers = [];
            var sequence = 1;
            form.find('.o_wslides_js_quiz_answers').each(function () {
                var value = $(this).find('input[type=text]').val();
                var answer = {
                    'sequence': sequence++,
                    'text_value': value,
                    'is_correct': $(this).find('input[type=radio]').prop('checked') == true
                };
                if ($(this).data('answer-id')) {
                    if (value.trim() !== "")
                        answerIDS.push($(this).data('answer-id'));
                    answer.id = $(this).data('answer-id');
                    answer.action = 'update';
                }
                if (value.trim() !== "") {
                    answers.push(answer);
                }
            });
            this.beforeUpdateIDS.forEach(function(id) {
                if (!answerIDS.includes(id))
                    answers.push({
                        'id': id,
                        'action': 'delete'
                    });
            });
            return {
                'id': this.$el.data('question-id'),
                'sequence': Number(this.$el.find('.o_wslides_quiz_question_sequence').text()),
                'question': form.find('.o_wslides_quiz_question input[type=text]').val(),
                'answer_ids': answers
            };
        },

        _displayCreatedQuestion: function (values) {
            this.$el.html(QWeb.render('slide.slide.quiz.question.updated', { question: values }));
            this.$el.addClass('completed-disabled');
            this.open = false;
        },

        _onUpdateClick: function(ev) {
            ev.preventDefault();
            var self = this;
            var form = this.$el.find('form');
            if (this._validForm(form)) {
                var values = this._getNewValues(form);
                console.log(values);
                return this._rpc({
                    route: '/slides/slide/quiz/update',
                    params: values
                }).then(function (response) {
                    response.sequence = values.sequence;
                    self._displayCreatedQuestion(response);
                }, function (error) {
                    self._alertShow(self.$el.find('form'), error.message.data.arguments[0]);
                });
            } else {
                this._alertShow(form, _t('There must be a text for the question'));
            }
        },

        _onCancelClick: function (ev) {
            ev.preventDefault();
            this._resetOldView();
        },

        _resetOldView: function() {
            this.$el.html(this.oldHtml);
            this.$el.addClass('completed-disabled');
        },

        reattachTo: function(element) {
            if (this._isOpen())
                this._resetOldView();
            this.setElement(element);
            this.renderElement();
        }

    });

    // TODO: Replace bus communication with trigger_up method (but how can I make this widget the parent ?)
    publicWidget.registry.websiteQuizCreation = publicWidget.Widget.extend({
        selector: '.o_wslides_js_quiz_container',
        xmlDependencies: ['/website_slides/static/src/xml/website_slides_quiz_creation.xml'],
        events: {
            'click .o_wslides_js_quiz_add': '_onQuizCreation',
            'click .o_wslides_js_quiz_edit_question': '_onEditQuestionClick',
            'click .o_wslides_js_quiz_delete_question': '_onDeleteQuestionClick',
        },
        /**
         * @override
         */
        start: function () {
            core.bus.on('onDeleteQuestion', this, this._onDeleteQuestion);
            core.bus.on('onCancelDeletion', this, this._onCancelDeletion);
            return this._super.apply(this, arguments);
        },

        _onQuizCreation: function (ev) {
            ev.preventDefault();
            if (!this.newQuestionWidget) {
                this.newQuestionWidget = new NewQuestionWidget(this, $(ev.currentTarget).data('slide-id'));
                this.newQuestionWidget.attachTo('.o_wslides_js_quiz_container');
            } else {
                this.newQuestionWidget.renderElement();
            }
        },

        _onEditQuestionClick: function (ev) {
            ev.preventDefault();
            if (!this.updateQuestionWidget) {
                this.updateQuestionWidget = new UpdateQuestionWidget(this);
                this.updateQuestionWidget.attachTo($(ev.currentTarget).closest('.o_wslides_js_lesson_quiz_question'));
            } else {
                this.updateQuestionWidget.reattachTo($(ev.currentTarget).closest('.o_wslides_js_lesson_quiz_question'));
            }
        },

        _onDeleteQuestionClick: function (ev) {
            var question = $(ev.currentTarget).closest('.o_wslides_js_lesson_quiz_question');
            this._showHideQuestion(question, 'hide');
            this.call('notification', 'notify', {
                Notification: QuestionDeletionNotification,
                title: _t('Deletion'),
                message: _.str.sprintf(_t("Click Undo to cancel, or in 5 seconds " +
                    "the question \"%s\" will be deleted"), question.data('title')),
                question: question
            });
        },

        _onDeleteQuestion: function(question) {
            this._rpc({
                route: '/slides/slide/quiz/delete',
                params: {
                    id: question.data('question-id')
                }
            }).then(function () {
                question.remove();
            }, function (error) {
                console.log(error);
            });
        },

        _onCancelDeletion: function(question) {
            this._showHideQuestion(question, 'show');
        },

        _showHideQuestion: function(question, action) {
            var followingQuestions = question.nextAll('.o_wslides_js_lesson_quiz_question').find('.o_wslides_quiz_question_sequence');
            followingQuestions.each(function () {
                if (action === 'hide')
                    $(this).text(Number($(this).text()) - 1);
                else
                    $(this).text(Number($(this).text()) + 1);
            });
            var $newQuestion = this.$el.find('.o_wslides_js_lesson_quiz_new_question .o_wslides_quiz_question_sequence');
            if (action === 'hide') {
                $newQuestion.text(Number($newQuestion.text()) - 1);
                if (this.newQuestionWidget)
                    this.newQuestionWidget.questionSequence--;
                question.hide();
            } else {
                $newQuestion.text(Number($newQuestion.text()) + 1);
                if (this.newQuestionWidget)
                    this.newQuestionWidget.questionSequence++;
                question.show();
            }
        },

    });

});