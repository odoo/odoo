var onYouTubeIframeAPIReady = undefined;

odoo.define('website_slides.fullscreen', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var QWeb = core.qweb;

    var session = require('web.session');

    var Quiz = require('website_slides.quiz');


    /**
     * Helper: Get the slide dict matching the given criteria
     *
     * @private
     * @param {Array<Object>} slideList List of dict reprensenting a slide
     * @param {Object} matcher (see https://underscorejs.org/#matcher)
     */
    var findSlide = function (slideList, matcher) {
        var slideMatch = _.matcher(matcher);
        return _.find(slideList, slideMatch);
    };

    /**
     * This widget is responsible of display Youtube Player
     *
     * The widget will trigger an event `change_slide` when the video is at
     * its end, and `slide_completed` when the player is at 30 sec before the
     * end of the video (30 sec before is considered as completed).
     */
    var VideoPlayer = publicWidget.Widget.extend({
        template: 'website.slides.fullscreen.video',
        youtubeUrl: 'https://www.youtube.com/iframe_api',

        init: function (parent, slide) {
            this.slide = slide;
            return this._super.apply(this, arguments);
        },
        start: function (){
            var self = this;
            return Promise.all([this._super.apply(this, arguments), this._loadYoutubeAPI()]).then(function() {
                self._setupYoutubePlayer();
            });
        },
        _loadYoutubeAPI: function () {
            var def = new Promise(function () {});
            if ($(document).find('script[src="' + this.youtubeUrl + '"]').length === 0) {
                var $youtubeElement = $('<script/>', {src: this.youtubeUrl});
                $(document.head).append($youtubeElement);

                // function called when the Youtube asset is loaded
                // see https://developers.google.com/youtube/iframe_api_reference#Requirements
                onYouTubeIframeAPIReady = function () {
                    def.resolve();
                };

            } else {
                def.resolve();
            }
            return def;
        },
        /**
         * Links the youtube api to the iframe present in the template
         *
         * @private
         */
        _setupYoutubePlayer: function (){
            this.player = new YT.Player('youtube-player' + this.slide.id, {
                host: 'https://www.youtube.com',
                playerVars: {
                    'autoplay': 1,
                    'origin': window.location.origin
                },
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
                                self.trigger_up('slide_to_complete', self.slide);
                            }
                        }
                    }
                }, 1000);
            }
            if (event.data === YT.PlayerState.ENDED){
                this.player = undefined;
                if (this.slide.hasNext) {
                    this.trigger_up('slide_go_next');
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
    var Sidebar = publicWidget.Widget.extend({
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
         * @param {Integer} slideId
         */
        setSlideCompleted: function (slideId) {
            var $elem = this.$('.fa-circle-thin[data-slide-id="'+slideId+'"]');
            $elem.removeClass('fa-circle-thin').addClass('fa-check text-success o_wslides_slide_completed');
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
        _getCurrentIndex: function () {
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
            ev.stopPropagation();
            var $elem = $(ev.currentTarget);
            var isQuiz = $elem.data('isQuiz');
            var slideID = parseInt($elem.data('id'));
            var slide = findSlide(this.slideEntries, {id: slideID, isQuiz: isQuiz});
            this.set('slideEntry', slide);
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
            var selector = '.o_wslides_fs_sidebar_list_item[data-id='+slide.id+'][data-is-quiz!="1"]';

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
    var Fullscreen = publicWidget.Widget.extend({
        events: {
            "click .o_wslides_fs_toggle_sidebar": '_onClickToggleSidebar',
        },
        custom_events: {
            'change_slide': '_onChangeSlideRequest',
            'slide_to_complete': '_onSlideToComplete',
            'slide_completed': '_onSlideCompleted',
            'slide_go_next': '_onSlideGoToNext',
        },
        /**
        * @override
        * @param {Object} el
        * @param {Object} slides Contains the list of all slides of the course
        * @param {integer} defaultSlideId Contains the ID of the slide requested by the user
        */
        init: function (el, slides, defaultSlideId){
            var result = this._super.apply(this,arguments);
            this.initialSlideID = defaultSlideId;
            this.slides = this._preprocessSlideData(slides);

            var slide;
            if (defaultSlideId) {
                slide = findSlide(this.slides, {id: defaultSlideId});
            } else {
                slide = this.slides[0];
            }

            this.set('slide', slide);

            this.sidebar = new Sidebar(this, this.slides, slide);
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
            if (slide.type === 'webpage' && !slide.isQuiz) {
                return this._fetchHtmlContent();
            }
            return Promise.resolve();
        },
        _markAsCompleted: function (slideId, completion) {
            var slide = findSlide(this.slides, {id: slideId});
            slide.completed = true;
            this.sidebar.setSlideCompleted(slide.id);
            this.sidebar.updateProgressbar(completion);
        },
        /**
         * Extend the slide data list to add informations about rendering method, and other
         * specific values according to their slide_type.
         */
        _preprocessSlideData: function (slidesDataList) {
            slidesDataList.forEach(function (slideData, index) {
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
                slideData.isQuiz = !!slideData.isQuiz;
                slideData.hasQuestion = !!slideData.hasQuestion;
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
            urlParts[urlParts.length-1] = this.get('slide').slug;
            var url =  urlParts.join('/');
            this.$('.o_wslides_fs_exit_fullscreen').attr('href', url);
            var fullscreenUrl = _.str.sprintf('%s?fullscreen=1', url);
            history.pushState(null, '', fullscreenUrl);
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

            // display quiz slide, or quiz attached to a slide
            if (slide.type === 'quiz' || slide.isQuiz) {
                var QuizWidget = new Quiz(this, slide);
                return QuizWidget.appendTo($content);
            }

            // render slide content
            if (_.contains(['document', 'presentation', 'infographic'], slide.type)) {
                $content.html(QWeb.render('website.slides.fullscreen.content', {widget: this}));
            } else if (slide.type === 'video') {
                this.videoPlayer = new VideoPlayer(this, slide);
                return this.videoPlayer.appendTo($content);
            } else if (slide.type === 'webpage'){
                var $wpContainer = $('<div>').addClass('o_wslide_fs_webpage_content bg-white block w-100 overflow-auto');
                $(slide.htmlContent).appendTo($wpContainer);
                $content.append($wpContainer);
            }
            return Promise.resolve();
        },
        /**
         * Once the completion conditions are filled,
         * rpc call to set the the relation between the slide and the user as "completed"
         *
         * @private
         * @param {Integer} slideId: the id of slide to set as completed
         */
        _setCompleted: function (slideId){
            var self = this;
            var slide = findSlide(this.slides, {id: slideId});
            if (!slide.completed) {  // no useless RPC call
                return this._rpc({
                    route: '/slides/slide/set_completed',
                    params: {
                        slide_id: slide.id,
                    }
                }).then(function (data){
                    self._markAsCompleted(slideId, data.channel_completion);
                });
            }
            return Promise.resolve();
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
        _onChangeSlide: function () {
            var self = this;
            var slide = this.get('slide');
            return this._fetchSlideContent().then(function() { // render content
                return self._renderSlide();
            }).then(function() {
                if (slide._autoSetDone && !session.is_website_user) {  // no useless RPC call
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
            var newSlide = findSlide(this.slides, {
                id: slideData.id,
                isQuiz: slideData.isQuiz || false,
            });
            this.set('slide', newSlide);
        },
        /**
         * Triggered when subwidget has mark the slide as done, and the UI need to be adapted.
         *
         * @private
         */
        _onSlideCompleted: function (ev) {
            var slide = ev.data.slide;
            var completion = ev.data.completion;
            this._markAsCompleted(slide.id, completion);
        },
        /**
         * Triggered when sub widget business is done and that slide
         * can now be marked as done.
         *
         * @private
         */
        _onSlideToComplete: function (ev) {
            if (!session.is_website_user) {  // no useless RPC call
                var slideId = ev.data.id;
                this._setCompleted(slideId);
            }
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
            this.$('.o_wslides_fs_sidebar').toggleClass('o_wslides_fs_sidebar_hidden');
            this.$('.o_wslides_fs_toggle_sidebar').toggleClass('active');
        },
    });

    publicWidget.registry.websiteSlidesFullscreenPlayer = publicWidget.Widget.extend({
        selector: '.o_wslides_fs_main',
        xmlDependencies: ['/website_slides/static/src/xml/website_slides_fullscreen.xml'],
        start: function (){
            var proms = [this._super.apply(this, arguments)];
            var fullscreen = new Fullscreen(this, this._getSlides(), this._getCurrentSlideID());
            proms.push(fullscreen.attachTo(".o_wslides_fs_main"));
            return Promise.all(proms);
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
            $slides.each(function () {
                var slideData = $(this).data();
                slideList.push(slideData);
            });
            return slideList;
        },
    });

    return Fullscreen;
});
