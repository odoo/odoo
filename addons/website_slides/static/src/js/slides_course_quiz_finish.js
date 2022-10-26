/** @odoo-module **/

import Dialog from 'web.Dialog';
import { _t } from 'web.core';

/**
 * This modal is used when the user finishes the quiz.
 * It handles the animation of karma gain and leveling up by animating
 * the progress bar and the text.
 */
var SlideQuizFinishModal = Dialog.extend({
    template: 'slide.slide.quiz.finish',
    events: {
        "click .o_wslides_quiz_modal_btn": '_onClickNext',
    },

    init: function(parent, options) {
        var self = this;
        this.quiz = options.quiz;
        this.hasNext = options.hasNext;
        this.userId = options.userId;
        options = _.defaults(options || {}, {
            size: 'medium',
            dialogClass: 'd-flex p-0',
            technical: false,
            renderHeader: false,
            renderFooter: false
        });
        this._super.apply(this, arguments);
        this.opened(function () {
            self._animateProgressBar();
            self._animateText();
        })
    },

    start: function() {
        var self = this;
        this._super.apply(this, arguments).then(function () {
            self.$modal.addClass('o_wslides_quiz_modal pt-5');
            self.$modal.find('.modal-dialog').addClass('mt-5');
            self.$modal.find('.modal-content').addClass('shadow-lg');
        });
    },

    //--------------------------------
    // Handlers
    //--------------------------------

    _onClickNext: function() {
        this.trigger_up('slide_go_next');
        this.destroy();
    },

    //--------------------------------
    // Private
    //--------------------------------

    /**
     * Handles the animation of the karma gain in the following steps:
     * 1. Initiate the tooltip which will display the actual Karma
     *    over the progress bar.
     * 2. Animate the tooltip text to increment smoothly from the old
     *    karma value to the new karma value and updates it to make it
     *    move as the progress bar moves.
     * 3a. The user doesn't level up
     *    I.   When the user doesn't level up the progress bar simply goes
     *         from the old karma value to the new karma value.
     * 3b. The user levels up
     *    I.   The first step makes the progress bar go from the old karma
     *         value to 100%.
     *    II.  The second step makes the progress bar go from 100% to 0%.
     *    III. The third and final step makes the progress bar go from 0%
     *         to the new karma value. It also changes the lower and upper
     *         bound to match the new rank.
     * @param $modal
     * @param rankProgress
     * @private
     */
    _animateProgressBar: function () {
        var self = this;
        this.$('[data-bs-toggle="tooltip"]').tooltip({
            trigger: 'manual',
            container: '.progress-bar-tooltip',
        }).tooltip('show');

        this.$('.tooltip-inner')
            .prop('karma', this.quiz.rankProgress.previous_rank.karma)
            .animate({
                karma: this.quiz.rankProgress.new_rank.karma
            }, {
                duration: this.quiz.rankProgress.level_up ? 1700 : 800,
                step: function (newKarma) {
                    self.$('.tooltip-inner').text(Math.ceil(newKarma));
                    self.$('[data-bs-toggle="tooltip"]').tooltip('update');
                }
            }
        );

        var $progressBar = this.$('.progress-bar');
        if (this.quiz.rankProgress.level_up) {
            this.$('.o_wslides_quiz_modal_title').text(_t('Level up!'));
            $progressBar.css('width', '100%');
            _.delay(function () {
                self.$('.o_wslides_quiz_modal_rank_lower_bound')
                    .text(self.quiz.rankProgress.new_rank.lower_bound);
                self.$('.o_wslides_quiz_modal_rank_upper_bound')
                    .text(self.quiz.rankProgress.new_rank.upper_bound || "");

                // we need to use _.delay to force DOM re-rendering between 0 and new percentage
                _.delay(function () {
                    $progressBar.addClass('no-transition').width('0%');
                }, 1);
                _.delay(function () {
                    $progressBar
                        .removeClass('no-transition')
                        .width(self.quiz.rankProgress.new_rank.progress + '%');
                }, 100);
            }, 800);
        } else {
            $progressBar.css('width', this.quiz.rankProgress.new_rank.progress + '%');
        }
    },

    /**
     * Handles the animation of the different text such as the karma gain
     * and the motivational message when the user levels up.
     * @private
     */
    _animateText: function () {
        var self = this;
       _.delay(function () {
            self.$('h4.o_wslides_quiz_modal_xp_gained').addClass('show in');
            self.$('.o_wslides_quiz_modal_dismiss').removeClass('d-none');
        }, 800);

        if (this.quiz.rankProgress.level_up) {
            _.delay(function () {
                self.$('.o_wslides_quiz_modal_rank_motivational').addClass('fade');
                _.delay(function () {
                    self.$('.o_wslides_quiz_modal_rank_motivational').html(
                        self.quiz.rankProgress.last_rank ?
                            self.quiz.rankProgress.description :
                            self.quiz.rankProgress.new_rank.motivational
                    );
                    self.$('.o_wslides_quiz_modal_rank_motivational').addClass('show in');
                }, 800);
            }, 800);
        }
    },

});

export default SlideQuizFinishModal;
