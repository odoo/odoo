var onYouTubeIframeAPIReady = undefined;

odoo.define('website_slides.fullscreen', function (require) {
    'use strict';
    var sAnimations = require('website.content.snippets.animation');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;

    var QuizWidget = require('website_slides.quiz');

    var tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);

    var Header = Widget.extend({
		events: {
            "click .o_wslides_fs_toggle_sidebar": '_onClickToggleSidebar'
        },
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Update the href for the "Write a review" button so that it always redirects
         * to the current slide details
         *
         * @public
         * @param {String} url
         */
        updateHref: function (url){
            this.$('.o_wslides_small_screen').attr('href', url);
        },
        updateTitle: function (data) {
            this.$('.o_wslides_fs_slide_title').empty().html(QWeb.render('website.course.fullscreen.title', data));
        },
        //--------------------------------------------------------------------------
        // Handler
        //--------------------------------------------------------------------------
        /**
         * When the user clicks the button "Lessons",
         * raise an event that will be caught by the Fullscreen widget
         *
         * @private
         * @param {*} ev
         */
		_onClickToggleSidebar: function (ev) {
			this.trigger_up('toggle_sidebar');
        },
	});

    var Sidebar = Widget.extend({
		events: {
            "click .o_wslides_fs_sidebar_slide_tab": '_onClickTab',
            "click .o_wslides_fs_slide_quiz": '_onClickMiniQuiz'
		},
		init: function (parent) {
            return this._super.apply(this, arguments);
        },
        start: function (){
            this.set('slideData', false);
            this.on('change:slideData', this, this._setCurrentSlide);
            var slideData =  this.$('.o_wslides_fs_sidebar_slide_tab.active').data();
            this.set('slideData',{
                slideID: slideData.id,
                isMiniQuiz: false
            });
        },
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Greens up the bullet when the slide is completed
         *
         * @public
         * @param {*} slide_id
         */
        setSlideCompleted: function (slide_id) {
            this.$('#check-'+slide_id).replaceWith($('<i class="check-done o_wslides_slide_completed fa fa-check-circle"></i>'));
        },
        /**
         * Hide or show the sidebar when the button "Lessons" is clicked
         *
         * @public
         */
		toggle: function () {
            this.$('.o_wslides_fs_sidebar').toggleClass('o_wslides_fs_sidebar_hidden');
            this.$('.o_wslides_fs_toggle_sidebar').toggleClass('active');
        },
        /**
         * Updates the progressbar whenever a lesson is completed
         *
         * @public
         * @param {*} channelCompletion
         */
        updateProgressbar: function (channelCompletion) {
            var completion = Math.min(100, channelCompletion);
            this.$('.o_wslides_fs_sidebar_progressbar > div').css('width', completion + "%" );
            this.$('.o_wslides_progress_percentage').text(completion);
        },
        //--------------------------------------------------------------------------
        // Handler
        //--------------------------------------------------------------------------
        /**
         * Handler called whenever the user clicks on a sub-quiz which is linked to a slide.
         * This does NOT handle the case of a slide of type "quiz".
         * By going through this handler, the widget will be able to determine that it has to render
         * the associated quiz and not the main content.
         *
         * @private
         * @param {*} ev
         */
        _onClickMiniQuiz: function (ev){
            var slideID = parseInt($(ev.currentTarget).data().slide_id);
            this.set('slideData',{
                slideID: slideID,
                isMiniQuiz: true
            });
            this.trigger_up('change_slide', this.get('slideData'));
        },
        /**
         * Handler called when the user clicks on a normal slide tab
         *
         * @private
         * @param {*} ev
         */
		_onClickTab: function (ev) {
            // trigger_up the event with slide id
            var slideID = parseInt($(ev.currentTarget).data().id);
			this.set('slideData',{
                slideID: slideID,
                isMiniQuiz: false
            });
            this.trigger_up('change_slide', this.get('slideData'));
        },
          /**
         * Actively changes the active tab in the sidebar so that it corresponds
         * the slide currently displayed
         *
         * @public
         */
        _setCurrentSlide: function () {
            var slideID = this.get('slideData').slideID;
            this.$('.o_wslides_fs_sidebar_slide_tab.active').removeClass('active');
            this.$('li.active').removeClass('active');
            this.$('.o_wslides_fs_sidebar_slide_tab[data-id='+slideID+']').addClass('active');
            this.$('li[slide_id='+slideID+']').addClass('active');
        },
	});

    var Fullscreen = Widget.extend({
        custom_events: {
            "toggle_sidebar": '_onToggleSidebar',
            "change_slide": '_onChangeSlideRequest',
        },
        /**
        * @override
        * @param {Object} el
        * @param {Object} slides Contains the list of all slides of the course
        * @param {Int} currentSlideID Contains the ID of the slide requested by the user
        */
        init: function (el, slides, currentSlideID){
            this._super.apply(this,arguments);
            this.initialSlideID = currentSlideID;
            this.slides = slides;
            this.set('slide', this._findSlideByID(currentSlideID));
            this.on('change:slide', this, this._onChangeSlide);
            this.url = undefined;
            this.player = undefined;
            this.header = new Header(this);
            this.sidebar = new Sidebar(this);
            this.templates = this._initTemplates();
        },
        /**
         * @override
         */
        start: function (){
            var def = this._super.apply(this, arguments);
            var self = this;
            this.url = window.location.pathname;
            return def.then(function (){
                self._initialSlideSetup();
                $(document).keydown(self._onKeyDown.bind(self));
            });
        },
        /**
         * @override
         */
        attachTo: function (){
            var defs = [this._super.apply(this, arguments)];
            defs.push(this.header.attachTo(this.$el));
            defs.push(this.sidebar.attachTo(this.$el));
            return $.when.apply($, defs);
        },
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        _initialSlideSetup: function (){
            var self = this;
            var currentSlide = self.get('slide');
            self._setPreviousAndNextSlides();
            self._fetchSlideContent().then(function (){
                self._renderSlideContent().then(function (){
                    if (_.contains(["presentation", "document", "infographic", "webpage"], currentSlide.slide_type) && !currentSlide.has_quiz){
                        self._setSlideStateAsDone();
                    }
                });
            });
        },
        _initTemplates: function (){
            return {
                'video': 'website.slides.fullscreen.video',
                'presentation': 'website.slides.fullscreen.presentation',
                'document': 'website.slides.fullscreen.presentation',
                'infographic': 'website.slides.fullscreen.infographic',
                'webpage': 'website.slides.fullscreen.webpage',
            };
        },
        /**
         * Fetches content with an rpc call for slides of type "webpage"
         *
         * @private
         */
        _fetchHtmlContent: function (){
            var self = this;
            var currentSlide = this.get('slide');
            return self._rpc({
                route:"/slide/html_content/get",
                params: {
                    'slide_id': currentSlide.id
                }
            }).then(function (data){
                if (data.html_content) {
                    currentSlide.htmlContent = data.html_content;
                    self.set('slide', currentSlide);
                }
            });
        },
        /**
        * Fetches slide content depending on its type.
        * If the slide doesn't need to fetch any content, return a resolved deferred
        *
        * @private
        */
        _fetchSlideContent: function (){
            var defs = [];
            var currentSlide = this.get('slide');

            if ((currentSlide.slide_type === 'quiz' || currentSlide.has_quiz) && !currentSlide.quiz ){
                defs.push(this._fetchQuiz());
            }
            if (currentSlide.slide_type === 'webpage' && !currentSlide.htmlContent) {
                defs.push(this._fetchHtmlContent());
            }
            return $.when.apply($, defs);
        },
        /**
         * Fetches quiz for the slides who have one
         *
         * @private
         * @param {object} slide
         */
        _fetchQuiz: function (){
            var self = this;
            var currentSlide = this.get('slide');
            return self._rpc({
                route:"/slide/quiz/get",
                params: {
                    'slide_id': currentSlide.id
                }
            }).then(function (data){
                if (data){
                    currentSlide.quiz = data;
                    currentSlide.quiz.reward = currentSlide.quiz.nb_attempts < 3 ? currentSlide.quiz.possible_rewards[currentSlide.quiz.nb_attempts] : currentSlide.quiz.possible_rewards[currentSlide.quiz.possible_rewards.length-1],
                    self.set('slide', currentSlide);
                }
            });
        },
        /**
         * Find and return the requested slide in the list "slides"
         *
         * @private
         * @param {Int} slideID Id of the requested slide
         */
        _findSlideByID: function (slideID){
            return _.find(this.slides, function (slide){
                return slide.id === slideID;
            });
        },
        /**
         * @private
         */
        _goToNextSlide: function (){
            var self = this;
            var currentSlide = this.get('slide');
            self.player = undefined;
            var goToQuiz = currentSlide.has_quiz && !currentSlide.goToQuiz && currentSlide.slide_type !== 'quiz';
            if (!goToQuiz && self.nextSlide){
                self.set('slide', self.nextSlide);
            } else if (goToQuiz){
                self.set('slide', _.extend({goToQuiz: goToQuiz}, currentSlide));
            } else if (self.nextSlide){
                self.set('slide', self.nextSlide);
            }
        },
        /**
         * @private
         */
        _goToPreviousSlide: function (){
            this.player = undefined;
            if (this.previousSlide){
                this.set('slide', this.previousSlide);
            }
        },
        /**
         * Binds left and right arrow to allow the user to navigate between slides
         *
         * @param {*} ev
         * @private
         */
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
        /**
         * Specific method of the youtube api.
         * Whenever the player starts playing, a setinterval is created.
         * This setinterval is used to check te user's progress in the video.
         * Once the user reaches a particular time in the video, the slide will be considered as completed if the video doesn't have a mini-quiz.
         * This method also allows to automatically go to the next slide (or the quiz associated to the current video) once the video is over
         *
         * @private
         * @param {*} event
         */
        _onPlayerStateChange: function (event){
            var self = this;
            var currentSlide = this.get('slide');
            clearInterval(self.tid);
            if (event.data === YT.PlayerState.PLAYING && !currentSlide.done) {
                self.tid = setInterval(function (){
                    if (event.target.getCurrentTime){
                        var currentTime = event.target.getCurrentTime();
                        var totalTime = event.target.getDuration();
                        if (totalTime && currentTime > totalTime - 30){
                            clearInterval(self.tid);
                            if (!currentSlide.has_quiz && !currentSlide.done){
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
         * Instanciate the quiz widget that will handle all the quiz functionalities
         *
         * @private
         */
        _renderQuiz: function (){
            var self = this;
            var currentSlide = this.get('slide');
            var Quiz = new QuizWidget(this, self.get('slide'), self.nextSlide);
            Quiz.appendTo('.o_wslides_fs_player');
            this.$('.next-slide').click(function (){
                self._goToNextSlide();
            });
            this.$('.back-to-video').click(function (){
                currentSlide.goToQuiz = false;
                self.set('slide', currentSlide);
            });
        },
        /**
         * Renders the current slide's content
         *
         * @private
         */
        _renderSlideContent: function (){
            var self = this;
            var currentSlide = this.get('slide');
            // this.$('.o_wslides_fs_player').empty();
            var defs = [];
            var template = this.templates[currentSlide.slide_type];
            if (template){
                defs.push($('.o_wslides_fs_player').html(QWeb.render(template, {
                    widget: this
                    }
                )));
                if (currentSlide.slide_type === "video"){
                    defs.push(self._renderYoutubeIframe());
                }
                if (currentSlide.slide_type === 'webpage'){
                    defs.push(self._renderWebpage());
                }
            }
            if (currentSlide.slide_type === "quiz" || currentSlide.goToQuiz){
                defs.push(self._renderQuiz());
            }
            return $.when.apply($, defs);
        },
        /**
         * Renders the content of a slide of type "webpage"
         *
         * @private
         */
        _renderWebpage: function (){
            var self = this;
            $(self.get('slide').htmlContent).appendTo('.o_wslides_fs_webpage_content');
        },
        /**
         * @private
         */
        _renderYoutubeIframe: function (){
            var self = this;
              /**
             * Due to issues of synchronization between the youtube api script and the widget's instanciation.
             */
            try {
                self._setupYoutubePlayer();
            }
            catch (err) {
                onYouTubeIframeAPIReady = function (){
                    var self = this;
                    self._setupYoutubePlayer();
                }.bind(this);
            }
        },
        /**
         * @private
         */
        _setPreviousAndNextSlides: function (){
            var currentSlide = this.get('slide');
            this.previousSlide = currentSlide !== _.first(this.slides) > 0 ? this.slides[_.findIndex(this.slides, function (s){
                return s.id === currentSlide.id;
            })-1] : undefined;
            this.nextSlide = currentSlide !== _.last(this.slides) ? this.slides[_.findIndex(this.slides, function (s){
                return s.id === currentSlide.id;
            })+1] : undefined;
        },
        /**
         * Once the completion conditions are filled,
         * rpc call to set the the relation between the slide and the user as "completed"
         *
         * @private
         */
        _setSlideStateAsDone: function (){
            var self = this;
            var currentSlide = this.get('slide');
            if (!currentSlide.done){
                self._rpc({
                    route: '/slides/slide/set_completed',
                    params: {
                        slide_id: currentSlide.id,
                    }
                }).then(function (data){
                    self.sidebar.setSlideCompleted(currentSlide.id);
                    currentSlide.done = true;
                    self.set('slide', currentSlide);
                    self.sidebar.updateProgressbar(data.channel_completion);
                });
            }
        },
        /**
         * Links the youtube api to the iframe present in the template
         *
         * @private
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
        _updateUI: function (currentSlide){
            this.sidebar.set('slideData', {
                slideID: currentSlide.id,
                isMiniQuiz: false
            });
            this.header.updateTitle({
                slide: currentSlide,
                miniQuiz: currentSlide.goToQuiz
            });
        },
        /**
         * Changes the url whenever the user changes slides.
         * This allows the user to refresh the page and stay on the right slide
         *
         * @private
         */
        _updateUrl: function (){
            var self = this;
            var url = window.location.pathname.split('/');
            url[url.length-1] = self.get('slide').slug;
            url = url.join('/');
            self.url = url;
            var urlToSmallScreen = self.url;
            self.url += "?fullscreen=1";
            self.header.updateHref(urlToSmallScreen);
            history.pushState(null,'',this.url);
        },
        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------
        /**
         * Method called whenever the user changes slides.
         * When the current slide is changed, it will autoimatically update the widget
         * and allow it to fetch the content if needs be, render it, update the url and set the
         * slide as "completed" if its type makes it necessary
         *
         * @private
         */
        _onChangeSlide: function (){
            clearInterval(this.tid);
            var currentSlide = this.get('slide');
            var self = this;
            this.player = undefined;
            self._fetchSlideContent().then(function (){
                self._renderSlideContent().then(function (){
                    if (_.contains(["presentation", "document", "infographic", "webpage"], currentSlide.slide_type) && !currentSlide.has_quiz){
                        self._setSlideStateAsDone();
                    }
                    self._updateUrl();
                    self._setPreviousAndNextSlides();
                    self._updateUI(currentSlide);
                });
            });
        },
        /**
         * Changes slide or not depending if the user is already on the "chosen" slide main content
         * but clicked on the sub-quiz or vice-versa
         *
         * @private
         * @param {int} slideID
         */
        _onChangeSlideRequest: function (ev){
            var requestedSlide = this._findSlideByID(ev.data.slideID);
            this.set('slide', _.extend({goToQuiz: ev.data.isMiniQuiz}, requestedSlide));
        },
        /**
         * Show or Hide the sidebar
         *
         * @private
         */
        _onToggleSidebar: function (){
            this.sidebar.toggle();
            this.$('.o_wslides_fs_player').toggleClass('o_wslides_fs_player_no_sidebar');
        },
    });

    sAnimations.registry.websiteSlidesFullscreenPlayer = Widget.extend({
        selector: '.o_wslides_fs_main',
        xmlDependencies: ['/website_slides/static/src/xml/website_slides_fullscreen.xml'],
        init: function (el){
            this._super.apply(this, arguments);
        },
        start: function (){
            var defs = [this._super.apply(this, arguments)];
            var fullscreen = new Fullscreen(this, this._getSlides(), this._getCurrentSlideID());
            defs.push(fullscreen.attachTo(".o_wslides_fs_main"));
            return $.when.apply($, defs);
        },
        _getCurrentSlideID: function (){
            return parseInt(this.$('.o_wslides_fs_sidebar_slide_tab.active').data().id);
        },
        /**
         * @private
         * Creates slides objects from every slide-list-cells attributes
         */
        _getSlides: function (){
            var slides = this.$('.o_wslides_fs_sidebar_slide_tab');
            var slideList = [];
            for (var i = 0; i < slides.length;i++){
                var slideData = $(slides[i]).data();
                slideData.embed_code = $(slideData.embed_code).attr('src');
                if (slideData.slide_type === 'video'){
                    slideData.embed_code =  "https://" + slideData.embed_code + "&rel=0&autoplay=1&enablejsapi=1&origin=" + window.location.origin;
                }
                slideList.push(slideData);
            }
            return slideList;
        },
    });
    return Fullscreen;
});