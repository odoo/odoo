var onYouTubeIframeAPIReady = undefined;

odoo.define('website_slides.fullscreen', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var QWeb = core.qweb;

    var tag = document.createElement('script');

    var QuizWidget = require('website_slides.quiz');

    tag.src = "https://www.youtube.com/iframe_api";
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);


    var Fullscreen = publicWidget.Widget.extend({
        /**
        * @override
        * @param {Object} el
        * @param {Object} data holding channelId and optionally upload and publish control parameters
        */
        init: function (el, courseId, slideId, userId) {
            this.courseID = parseInt(courseId, 10);
            this.slideID = parseInt(slideId, 10);
            this.userID = parseInt(userId, 10);
            this.course = undefined;
            this.slide = undefined;
            this.slides = [];
            this.nextSlide = undefined;
            this.previousSlide = undefined;
            this.url = undefined;
            this.urlToSmallScreen = undefined;
            this.activetab = undefined;
            this.player = undefined;
            this.goToQuiz = false;
            this.answeredQuestions = [];
            this.slideTitle = undefined;
            return this._super.apply(this,arguments);
        },
        start: function (){
            this.url = window.location.pathname;
            this.urlToSmallScreen = this.url.replace('/fullscreen','');
            this._getSlides();
            this._renderPlayer();
            this._bindListEvents();
            $(document).keydown(this._onKeyDown.bind(this));
            return this._super.apply(this, arguments);
        },
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
         /**
         * @private
         * Renders the player accordingly to the current slide
         */
        _renderPlayer: function (){
            var self = this;
            var embed_url;
            if (self.slide.slide_type !== 'webpage' || self.slide.htmlContent){
                if ((self.slide.slide_type === "quiz" || self.slide.has_quiz) && !self.slide.quiz){
                    self._fetchQuiz();
                } else {
                    embed_url = $(this.slide.embed_code).attr('src');
                    if (self.slide.slide_type === "video"){
                        embed_url = "https://" + embed_url + "&rel=0&autoplay=1&enablejsapi=1&origin=" + window.location.origin;
                    }
                    $('.o_wslides_fs_player').html(QWeb.render('website.slides.fullscreen', {
                        slide: self.slide,
                        nextSlide: self.nextSlide,
                        questions: self.slide.quiz ? self.slide.quiz.questions: '',
                        reward: self.slide.quiz ? self.slide.quiz.nb_attempts < 3 ? self.slide.quiz.possible_rewards[self.slide.quiz.nb_attempts] : self.slide.quiz.possible_rewards[3]: self.slide.maxPoints,
                        embed_url: embed_url,
                        question_count: self.slide.quiz ? self.slide.quiz.questions.length : '',
                        letters: self.slide.quiz ? self.letters : '',
                        showMiniQuiz: self.goToQuiz
                    }));
                    if (self.slide.slide_type === "video"){
                      self._renderYoutubeIframe();
                    }
                    if (self.slide.slide_type === 'webpage'){
                        self._renderWebpage();
                    }
                    if ((self.slide.slide_type === "presentation" || self.slide.slide_type === "document" || self.slide.slide_type === "infographic" || self.slide.slide_type === "webpage") && !self.slide.quiz){
                        self._setSlideStateAsDone();
                    }
                    if ((self.slide.quiz && self.slide.slide_type === "quiz") || self.goToQuiz){
                        self._renderQuiz();
                    }
                }
            } else {
                self._fetchHtmlContent();
            }
            self._renderTitle();
        },
        _renderYoutubeIframe: function (){
            var self = this;
              /**
             * Due to issues of synchronization between the youtube api script and the widget's instanciation.
             */
            try {
                self._setupYoutubePlayer();
            }
            catch (e) {
                onYouTubeIframeAPIReady = function (){
                    var self = this;
                    self._setupYoutubePlayer();
                }.bind(this);
            }
        },
        _renderWebpage: function (){
            var self = this;
            $(self.slide.htmlContent).appendTo('.o_wslides_fs_webpage_content');
        },
        _renderQuiz: function (){
            var self = this;
            var Quiz = new QuizWidget(this, self.slide, self.nextSlide);
            Quiz.appendTo('.o_wslides_fs_player');
            $('.next-slide').click(function (){
                self._goToNextSlide();
            });
            $('.back-to-video').click(function (){
                self.goToQuiz = false;
                self._renderPlayer();
            });
        },
        _renderTitle: function (){
            var self = this;
            $('.o_wslides_fs_slide_title').empty().html(QWeb.render('website.course.fullscreen.title', {
                slide: self.slide,
                miniQuiz: self.goToQuiz
            }));
        },
        /**
         * @private
         * Links the youtube api to the iframe present in the template
         */
        _setupYoutubePlayer: function (){
            var self = this;
            self.player = new YT.Player('youtube-player', {
                host: 'https://www.youtube.com',
                playerVars: {'autoplay': 1, 'origin': window.location.origin},
                autoplay: 1,
                events: {
                    'onReady': self._onPlayerReady,
                    'onStateChange': this._onPlayerStateChange.bind(self)
                }
            });
        },
        /**
         * @param {*} event
         * Specific method of the youtube api.
         * Whenever the player starts playing, a setinterval is created.
         * This setinterval is used to check te user's progress in the video.
         * Once the user reaches a particular time in the video, the slide will be considered as completed if the video doesn't have a mini-quiz.
         * This method also allows to automatically go to the next slide (or the quiz associated to the current video) once the video is over
         */
        _onPlayerStateChange: function (event){
            var self = this;
            var tid;
            clearInterval(self.tid);
            if (event.data === YT.PlayerState.PLAYING && !self.slide.done) {
                self.tid = setInterval(function (){
                    if (event.target.getCurrentTime){
                        var currentTime = event.target.getCurrentTime();
                        var totalTime = event.target.getDuration();
                        if (totalTime && currentTime > totalTime - 30){
                            clearInterval(self.tid);
                            if (!self.slide.has_quiz && !self.slide.done){
                                self.slide.done = true;
                                self._setSlideStateAsDone();
                            }
                        }
                    }
                }, 1000);
            }
            if (event.data === YT.PlayerState.ENDED){
                self.player = undefined;
                self._goToNextSlide();
            }
        },
        /**
         * @private
         * Creates slides objects from every slide-list-cells attributes
         */
        _getSlides: function (){
            var self = this;
            var slides = $('.o_wslides_fs_sidebar_slide_tab');
            for (var i = 0; i < slides.length;i++){
                var slide = $(slides[i]);
                self.slides.push(slide.data());
                this._getActiveSlide();
            }
        },
        /**
         * @private
         * @param {object} slide
         * Fetch the quiz for a particular slide
         */
        _fetchQuiz: function (){
            var self = this;
            self._rpc({
                route:"/slide/quiz/get",
                params: {
                    'slide_id': self.slide.id
                }
            }).then(function (data){
                if (data){
                    self.slide.quiz = data;
                    self._renderPlayer();
                }
            });
        },
        _fetchHtmlContent: function (){
            var self = this;
            self._rpc({
                route:"/slide/html_content/get",
                params: {
                    'slide_id': self.slide.id
                }
            }).then(function (data){
                if (data.html_content) {
                    self.slide.htmlContent = data.html_content;
                    self._renderPlayer();
                }
            });
        },
        /**
         * @private
         * Once the completion conditions are filled,
         * sends a json request to the backend to set the relation between the slide and the user as being completed
         */
        _setSlideStateAsDone: function (){
            var self = this;
            self._rpc({
                route: '/slides/slide/set_completed',
                params: {
                    slide_id: self.slide.id,
                }
            }).then(function (data) {
                if (! data.error) {
                    $('#check-'+self.slide.id).replaceWith($('<i class="check-done o_wslides_slide_completed fa fa-check-circle"></i>'));
                    self.slide.done = true;
                    clearInterval(self.tid);
                    self.channelCompletion = data.channel_completion;
                    self._updateProgressbar();
                }
            });
        },
        _updateProgressbar: function () {
            var completion = _.min([this.channelCompletion, 100]);
            this.$('.o_wslides_fs_sidebar_progressbar .progress-bar').css('width', completion + "%" );
            this.$('.o_wslides_progress_percentage').text(completion);
        },
        /**
         * @private
         * Creates an array of letters to be used in the quiz with a foreach
         */
        _generateQuizLetters: function (){
            var letters = [];
            for (var i = 65; i < 91; i++){
                letters.push(String.fromCharCode(i));
            }
            return letters;
        },
        _goToNextSlide: function (){
            var self = this;
            clearInterval(self.tid);
            self.player = undefined;
            self.goToQuiz = self.slide.has_quiz && !self.goToQuiz && self.slide.slide_type !== 'quiz';
            if (self.nextSlide && !self.goToQuiz){
                self.slide = self.nextSlide;
                self.index++;
                self._setActiveTab();
                self._renderPlayer();
                self._setPreviousAndNextSlides();
                self._updateUrl();
                history.pushState(null,'',self.url);
            }
            else if (self.nextSlide){
                self._renderPlayer();
            }
        },
        _goToPreviousSlide: function (){
            var self = this;
            clearInterval(self.tid);
            self.goToQuiz = false;
            self.player = undefined;
            if (self.previousSlide){
                self.slide = self.previousSlide;
                self.index--;
                self._setActiveTab();
                self._renderPlayer();
                self._setPreviousAndNextSlides();
                self._updateUrl();
                history.pushState(null,'',self.url);
            }
        },
        _setPreviousAndNextSlides: function (){
            var self = this;
            self.previousSlide = self.index > 0 ? self.slides[self.index-1] : undefined;
            self.nextSlide = self.index < (self.slides.length - 1) ? self.slides[self.index+1] : undefined;
        },
        /**
         * Changes the url whenever the user changes slides.
         * This allows the user to refresh the page and stay at the right video
         */
        _updateUrl: function (){
            var self = this;
            var url = window.location.pathname.split('/');
            url[url.length-1] = self.slide.slug;
            url = url.join('/');
            self.url = url;
            self.urlToSmallScreen = self.url;
            self.url += "?fullscreen=1";
            $('.o_wslides_small_screen').attr('href', self.urlToSmallScreen);
        },
        /**
         * Whenever the user changes slide, change the active tab
         */
        _setActiveTab: function (){
            var self = this;
            self.activeTab.removeClass('active');
            $('li.active').removeClass('active');
            $('li[data-slide-id='+self.slide.id+']').addClass('active');
            self.activeTab = $('.o_wslides_fs_sidebar_slide_tab[index="'+self.index+'"]');
            self.activeTab.addClass('active');
        },
        /**
         * The first time the user gets on the player,
         * get the slide that is represented by the active tab in the sidebar
         */
        _getActiveSlide: function (){
            var self = this;
            self.activeTab = $('.o_wslides_fs_sidebar_slide_tab.active');
            self.index = parseInt(self.activeTab.attr('index'), 10);
            self.slide = self.slides[self.index];
            self._setPreviousAndNextSlides();
        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        _onListCellClick: function (ev){
            var self = this;
            clearInterval(self.tid);
            self.player = undefined;
            var target = $(ev.currentTarget);
            self.goToQuiz = false;
            if (target[0] !== self.activeTab[0]){
                self.activeTab.removeClass('active');
                target.addClass('active');
                self.index = parseInt(target.attr('index'));
                self._getActiveSlide();
                self._renderPlayer();
                $('li.active').removeClass('active');
                $('li[data-slide-id='+self.slide.id+']').addClass('active');
                self._setPreviousAndNextSlides();
                self._updateUrl();
                history.pushState(null,'',self.url);
            }
        },
        _sidebarToggle: function (ev){
            ev.preventDefault();
            $(ev.currentTarget).toggleClass('active');
            $('.o_wslides_fs_sidebar').toggleClass('o_wslides_fs_sidebar_hidden');
            $('.o_wslides_fs_player').toggleClass('o_wslides_fs_player_no_sidebar');
        },
        _onMiniQuizClick: function (ev){
            var self = this;
            self.index = parseInt($(ev.currentTarget).attr('index'));
            self.slide = self.slides[self.index];
            self.goToQuiz = true;
            self._setPreviousAndNextSlides();
            self._renderPlayer();
            self._setActiveTab();
            self._updateUrl();
            history.pushState(null,'' ,self.url);
        },
         /**
        * @private
        * Binds events related to the list
        */
        _bindListEvents: function (){
            var self = this;
            $('.o_wslides_fs_sidebar_slide_tab').each(function () {
                $(this).click(self._onListCellClick.bind(self));
            });
            $('.o_wslides_fs_slide_quiz ').each(function (){
                $(this).click(self._onMiniQuizClick.bind(self));
            });
            $('.o_wslides_fs_toggle_sidebar').click(function (ev){
                self._sidebarToggle(ev);
            });
        },
        _onKeyDown: function (ev){
            var self = this;
            switch (ev.key){
                case "ArrowRight":
                self._goToNextSlide();
                break;
                case "ArrowLeft":
                self._goToPreviousSlide();
                break;
            }
        },
    });

    publicWidget.registry.websiteSlidesFullscreenPlayer = publicWidget.Widget.extend({
        selector: '.o_wslides_fs_main',
        xmlDependencies: ['/website_slides/static/src/xml/website_slides_fullscreen.xml'],
        init: function (el){
            this._super.apply(this, arguments);
        },
        start: function (){
            var defs = [this._super.apply(this, arguments)];
            var userId = this.$el.data('userId');
            var courseId = this.$el.data('courseId');
            var slideId = this.$el.data('slideId');
            var fullscreen = new Fullscreen(this, courseId, slideId, userId);
            defs.push(fullscreen.attachTo(this.$el));
            return $.when.apply($, defs);
        }
    });

    return Fullscreen;
});
