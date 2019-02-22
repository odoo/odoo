var onYouTubeIframeAPIReady = undefined;

odoo.define('website_slides.fullscreen', function (require) {
    'use strict';
    var sAnimations = require('website.content.snippets.animation');
    var Widget = require('web.Widget');
    var core = require('web.core');
    var QWeb = core.qweb;

    var Quiz = require('website_slides.quiz');

    /**
     * This widget is responsible of display Youtube Player
     *
     * The widget will trigger an event `change_slide` when the video is at
     * its end, and `slide_completed` when the player is at 30 sec before the
     * end of the video (30 sec before is considered as completed).
     */
    var VideoPlayer = Widget.extend({
        template: 'website.slides.fullscreen.video',
        youtubeUrl: 'https://www.youtube.com/iframe_api',

        init: function (parent, slide) {
            this.slide = slide;
            return this._super.apply(this, arguments);
        },
        start: function (){
            return $.when(this._super.apply(this, arguments), this._loadYoutubeAPI());
        },
        _loadYoutubeAPI: function () {
            var def = $.Deferred();
            if(!document.querySelector('script[src="' + this.youtubeUrl + '"]')) {
                var tag = document.createElement('script');
                tag.setAttribute('src', this.youtubeUrl);
                tag.onload = function() {
                    def.resolve();
                };
                document.head.appendChild(tag);
            } else {
                def.resolve();
            }
            return def;
        },
        /**
         * When attaching event to widget DOM (setElement, or start, or attachTo), we need to rebind
         * Youtube player to the div from the template.
         *
         * @private
         */
        _delegateEvents: function (){
            var res = this._super.apply(this, arguments);
            try {  // Due to issues of synchronization between the youtube api script and the widget's instanciation.
                this._setupYoutubePlayer();
            } catch (err) {
                onYouTubeIframeAPIReady = function () {
                    this._setupYoutubePlayer();
                }.bind(this);
            }
            return res;
        },
        /**
         * Links the youtube api to the iframe present in the template
         *
         * @private
         */
        _setupYoutubePlayer: function (){
            this.player = new YT.Player('youtube-player', {
                host: 'https://www.youtube.com',
                playerVars: {
                    'autoplay': 1,
                    'origin': window.location.origin
                },
                autoplay: 1,
                events: {
                    'onStateChange': this._onPlayerStateChange.bind(this)
                }
            });
        },
        /**
         * Specific method of the youtube api.
         * Whenever the player starts playing, a setinterval is created.
         * This setinterval is used to check te user's progress in the video.
         * Once the user reaches a particular time in the video, the slide will be considered as completed
         * if the video doesn't have a mini-quiz.
         * This method also allows to automatically go to the next slide (or the quiz associated to the current
         * video) once the video is over
         *
         * @private
         * @param {*} event
         */
        _onPlayerStateChange: function (event){
            var self = this;
            clearInterval(self.tid);
            if (event.data === YT.PlayerState.PLAYING && !self.slide.completed) {
                self.tid = setInterval(function (){
                    if (event.target.getCurrentTime){
                        var currentTime = event.target.getCurrentTime();
                        var totalTime = event.target.getDuration();
                        if (totalTime && currentTime > totalTime - 30){
                            clearInterval(self.tid);
                            if (!self.slide.hasQuestion && !self.slide.completed){
                                self.trigger_up('slide_completed', self.slide);
                            }
                        }
                    }
                }, 1000);
            }
            if (event.data === YT.PlayerState.ENDED){
                self.player = undefined;
                if (self.slide.hasNext) {
                    self.trigger_up('slide_go_next');
                }
            }
        },
    });


    /**
     * This widget is responsible of navigation for one slide to another:
     *  - by clicking on any slide list entry
     *  - by mouse click (next / prev)
     *  - by recieving the order to go to prev/next slide (`goPrevious` and `goNext` public methods)
     *
     * The widget will trigger an event `change_slide` with
     * the `slideId` and `isMiniQuiz` as data.
     */
    var Sidebar = Widget.extend({
        events: {
            "click .o_wslides_fs_sidebar_list_item": '_onClickTab',
        },
        init: function (parent, slideList, defaultSlide) {
            var result = this._super.apply(this, arguments);
            this.slideEntries = slideList;
            this.set('slideEntry', defaultSlide);
            return result;
        },
        start: function (){
            var self = this;
            this.on('change:slideEntry', this, this._onChangeCurrentSlide);
            return this._super.apply(this, arguments).then(function (){
                $(document).keydown(self._onKeyDown.bind(self));
            });
        },
        destroy: function () {
            $(document).unbind('keydown', this._onKeyDown.bind(this));
            return this._super.apply(this, arguments);
        },
        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------
        /**
         * Change the current slide with the next one (if there is one).
         *
         * @public
         */
        goNext: function () {
            var currentIndex = this._getCurrentIndex();
            if (currentIndex < this.slideEntries.length-1) {
                this.set('slideEntry', this.slideEntries[currentIndex+1]);
            }
        },
        /**
         * Change the current slide with the previous one (if there is one).
         *
         * @public
         */
        goPrevious: function () {
            var currentIndex = this._getCurrentIndex();
            if (currentIndex >= 1) {
                this.set('slideEntry', this.slideEntries[currentIndex-1]);
            }
        },
        /**
         * Greens up the bullet when the slide is completed
         *
         * @public
         * @param {*} slide_id
         */
        setSlideCompleted: function (slideId) {
            var $elem = this.$('.fa-circle-thin[data-slide-id="'+slideId+'"]');
            $elem.removeClass('fa-circle-thin').addClass('fa-check-circle text-success');
        },
        /**
         * Updates the progressbar whenever a lesson is completed
         *
         * @public
         * @param {*} channelCompletion
         */
        updateProgressbar: function (channelCompletion) {
            var completion = Math.min(100, channelCompletion);
            this.$('.progress-bar').css('width', completion + "%" );
            this.$('.o_wslides_progress_percentage').text(completion);
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Get the index of the current slide entry (slide and/or quiz)
         */
        _getCurrentIndex: function() {
            var slide = this.get('slideEntry');
            var currentIndex = _.findIndex(this.slideEntries, function (entry) {
                return entry.id === slide.id && entry.isQuiz === slide.isQuiz;
            });
            return currentIndex;
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
            this.set('slideEntry',{
                slideID: slideID,
                isMiniQuiz: true
            });
            this.trigger_up('change_slide', this.get('slideEntry'));
        },
        /**
         * Handler called when the user clicks on a normal slide tab
         *
         * @private
         * @param {*} ev
         */
        _onClickTab: function (ev) {
            var $elem = $(ev.currentTarget);
            var isQuiz = $elem.data('isQuiz');
            var slideID = parseInt($elem.data('id'));
            var slide = _.filter(this.slideEntries, function (entry) {
                return entry.id === slideID && entry.isQuiz == isQuiz;
            });
            this.set('slideEntry', slide[0]);
        },
        /**
         * Actively changes the active tab in the sidebar so that it corresponds
         * the slide currently displayed
         *
         * @private
         */
        _onChangeCurrentSlide: function () {
            var slide = this.get('slideEntry');
            this.$('.o_wslides_fs_sidebar_list_item.active').removeClass('active');
            var selector = '.o_wslides_fs_sidebar_list_item[data-id='+slide.id+']';
            if (slide.isQuiz) {
                selector += '[data-is-quiz="1"]';
            } else {
                selector += '[data-is-quiz!="1"]';
            }
            this.$(selector).addClass('active');
            this.trigger_up('change_slide', this.get('slideEntry'));
        },

        /**
         * Binds left and right arrow to allow the user to navigate between slides
         *
         * @param {*} ev
         * @private
         */
        _onKeyDown: function (ev){
            switch (ev.key){
                case "ArrowLeft":
                    this.goPrevious();
                    break;
                case "ArrowRight":
                    this.goNext();
                    break;
            }
        },
    });


    /**
     * This widget's purpose is to show content of a course, naviguating through contents
     * and correclty display it. It also handle slide completion, course progress, ...
     *
     * This widget is rendered sever side, and attached to the existing DOM.
     */
    var Fullscreen = Widget.extend({
        events: {
            "click .o_wslides_fs_toggle_sidebar": '_onClickToggleSidebar',
        },
        custom_events: {
            'change_slide': '_onChangeSlideRequest',
            'toggle_sidebar': '_onToggleSidebar',
            'slide_completed': '_onSlideCompleted',
            'quiz_completed': '_onSlideCompleted',
            'slide_go_next': '_onSlideGoToNext',
        },
        /**
        * @override
        * @param {Object} el
        * @param {Object} slides Contains the list of all slides of the course
        * @param {Int} defaultSlideId Contains the ID of the slide requested by the user
        */
        init: function (el, slides, defaultSlideId){
            var result = this._super.apply(this,arguments);
            this.initialSlideID = defaultSlideId;
            this.slides = this._preprocessSlideData(slides);

            var slide;
            if (defaultSlideId) {
                slide = this._findSlide({id: defaultSlideId});
            } else {
                slide = this.slides[0];
            }

            this.set('slide', slide);

            // extract data for sidebar
            var sidebarData = _.map(this.slides, function(slide) {
                return {
                    id: slide.id,
                    hasNext: slide.hasNext,
                    isQuiz: slide.isQuiz,
                }
            });
            this.sidebar = new Sidebar(this, sidebarData, {
                id: slide.id,
                isQuiz: slide.isQuiz,
                hasNext: slide.hasNext,
            });
            return result;
        },
        /**
         * @override
         */
        start: function (){
            var self = this;
            this.on('change:slide', this, this._onChangeSlide);
            return this._super.apply(this, arguments).then(function () {
                self._onChangeSlide(); // trigger manually once DOM ready, since slide content is not rendered server side
            });
        },
        /**
         * Extended to attach sub widget to sub DOM. This might be experimental but
         * seems working fine.
         *
         * @override
         */
        attachTo: function (){
            var defs = [this._super.apply(this, arguments)];
            defs.push(this.sidebar.attachTo(this.$('.o_wslides_fs_sidebar')));
            return $.when.apply($, defs);
        },
        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------
        /**
         * Fetches content with an rpc call for slides of type "webpage"
         *
         * @private
         */
        _fetchHtmlContent: function (){
            var self = this;
            var currentSlide = this.get('slide');
            return self._rpc({
                route:"/slides/slide/get_html_content",
                params: {
                    'slide_id': currentSlide.id
                }
            }).then(function (data){
                if (data.html_content) {
                    currentSlide.htmlContent = data.html_content;
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
            var slide = this.get('slide');
            if (slide.type === 'webpage') {
                return this._fetchHtmlContent();
            }
            return $.when();
        },
        /**
         * Get the slide dict matching the given criteria
         *
         * @private
         * @param {Object} matcher (see https://underscorejs.org/#matcher)
         */
        _findSlide: function (matcher) {
            var slideMatch = _.matcher(matcher);
            var result = _.filter(this.slides, slideMatch);
            return result[0];
        },
        /**
         * Extend the slide data list to add informations about rendering method, and other
         * specific values according to their slide_type.
         */
        _preprocessSlideData: function(slidesDataList) {
            _.each(slidesDataList, function (slideData, index) {
                // compute hasNext slide
                slideData.hasNext = index < slidesDataList.length-1;
                // compute embed url
                if (slideData.type === 'video') {
                    slideData.embedCode = $(slideData.embedCode).attr('src');  // embedCode containts an iframe tag, where src attribute is the url (youtube or embed document from odoo)
                    slideData.embedUrl =  "https://" + slideData.embedCode + "&rel=0&autoplay=1&enablejsapi=1&origin=" + window.location.origin;
                } else if (slideData.type === 'infographic') {
                    slideData.embedUrl = _.str.sprintf('/web/image/slide.slide/%s/image', slideData.id);
                } else if (_.contains(['document', 'presentation'], slideData.type)) {
                    slideData.embedUrl = $(slideData.embedCode).attr('src');
                }
                // fill empty property to allow searching on it with _.filter(list, matcher)
                slideData.isQuiz = slideData.isQuiz ? true : false;
                slideData.hasQuestion = slideData.hasQuestion ? true : false;
                // technical settings for the Fullscreen to work
                slideData._autoSetDone = _.contains(['infographic', 'presentation', 'document', 'webpage'], slideData.type) && !slideData.hasQuestion;
            });
            return slidesDataList;
        },
        /**
         * Changes the url whenever the user changes slides.
         * This allows the user to refresh the page and stay on the right slide
         *
         * @private
         */
        _pushUrlState: function (){
            var urlParts = window.location.pathname.split('/');
            urlParts[urlParts.length-1] = this.get('slide').id;
            var url = _.str.sprintf('%s?fullscreen=1', urlParts.join('/'));
            history.pushState(null, '', url);
        },
        /**
         * Render the current slide content using specific mecanism according to slide type:
         * - simply append content (for webpage)
         * - template rendering (for image, document, ....)
         * - using a sub widget (quiz and video)
         *
         * @private
         * @returns Deferred
         */
        _renderSlide: function () {
            var slide = this.get('slide');
            var $content = this.$('.o_wslides_fs_content');
            $content.empty();
            $content.removeClass('bg-white'); // webpage case

            // display quiz slide, or quiz attached to a slide
            if (slide.type === 'quiz' || slide.isQuiz) {
                var QuizWidget = new Quiz(this, this.get('slide'));
                return QuizWidget.appendTo($content);
            }

            // render slide content
            if (_.contains(['document', 'presentation', 'infographic'], slide.type)) {
                $content.html(QWeb.render('website.slides.fullscreen.content', {widget: this}));
            } else if (slide.type === 'video') {
                this.videoPlayer = new VideoPlayer(this, slide);
                return this.videoPlayer.appendTo($content);
            } else if (slide.type === 'webpage'){
                $(slide.htmlContent).appendTo($content);
                $content.addClass('bg-white');
            }
            return $.when();
        },
        /**
         * Once the completion conditions are filled,
         * rpc call to set the the relation between the slide and the user as "completed"
         *
         * @private
         * @param slideId: the id of slide to set as completed
         */
        _setCompleted: function (slideId){
            var self = this;
            var slide = this._findSlide({id: slideId});
            if (!slide.completed) {  // no useless RPC call
                return this._rpc({
                    route: '/slides/slide/set_completed',
                    params: {
                        slide_id: slide.id,
                    }
                }).then(function (data){
                    slide.completed = true;
                    self.sidebar.setSlideCompleted(slide.id);
                    self.sidebar.updateProgressbar(data.channel_completion);
                });
            }
            return $.when();
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
            var self = this;
            var slide = this.get('slide');
            return this._fetchSlideContent().then(function() { // update title and render content
                self.$('.o_wslides_fs_slide_title').html(QWeb.render('website.slides.fullscreen.title', {widget: self}));
                return self._renderSlide();
            }).then(function() {
                if (slide._autoSetDone) {
                    self._setCompleted(slide.id);
                }
                self._pushUrlState();
            });
        },
        /**
         * Changes current slide when receiving custom event `change_slide` with
         * its id and if it's its quizz or not we need to display.
         *
         * @private
         */
        _onChangeSlideRequest: function (ev){
            var slideData = ev.data;
            var newSlide = this._findSlide({
                id: slideData.id,
                isQuiz: slideData.isQuiz || false,
            });
            this.set('slide', newSlide);
        },
        /**
         * Triggered when sub widget business is done and that slide
         * can now be marked as done.
         *
         * @private
         */
        _onSlideCompleted: function (ev) {
            var slideId = ev.data.id;
            this._setCompleted(slideId);
        },
        /**
         * Go the next slide
         *
         * @private
         */
        _onSlideGoToNext: function (ev) {
            this.sidebar.goNext();
        },
        /**
         * Show or Hide the sidebar
         *
         * @private
         */
        _onClickToggleSidebar: function (ev){
            ev.preventDefault();
            this.$('.o_wslides_fs_sidebar').toggleClass('d-none');
            this.$('.o_wslides_fs_content').toggleClass('col-10');
            this.$('.o_wslides_fs_content').toggleClass('col-12');
            this.$('.o_wslides_fs_toggle_sidebar').toggleClass('active');
        },
    });

    sAnimations.registry.websiteSlidesFullscreenPlayer = Widget.extend({
        selector: '.o_wslides_fs_main',
        xmlDependencies: ['/website_slides/static/src/xml/website_slides_fullscreen.xml'],
        start: function (){
            var defs = [this._super.apply(this, arguments)];
            var fullscreen = new Fullscreen(this, this._getSlides(), this._getCurrentSlideID());
            defs.push(fullscreen.attachTo(".o_wslides_fs_main"));
            return $.when.apply($, defs);
        },
        _getCurrentSlideID: function (){
            return parseInt(this.$('.o_wslides_fs_sidebar_list_item.active').data('id'));
        },
        /**
         * @private
         * Creates slides objects from every slide-list-cells attributes
         */
        _getSlides: function (){
            var $slides = this.$('.o_wslides_fs_sidebar_list_item');
            var slideList = [];
            $slides.each(function() {
                var slideData = $(this).data();
                slideList.push(slideData);
            });
            return slideList;
        },
    });

    return Fullscreen;
});