odoo.define('website_slides.slideslist', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');

    var SlideUpload = require('website_slides.upload_modal');

    var List = publicWidget.Widget.extend({
        init: function (el){
            this._super.apply(this,arguments);
            this.draggedElement = undefined;
            this.dropTarget = undefined;
            this.slideCount = undefined;
            this.slides = [];
            this.categories = [];
        },
        start: function (){
            this._super.apply(this,arguments);
            this.slideCount = $('li.content-slide').length;
            //Change links HREF to fullscreen mode for SEO
            var links = $(".link-to-slide");
            for (var i = 0; i < links.length; i++){
                $(links[i]).attr('href', $(links[i]).attr('href') + "?fullscreen=1");
            }
            this._bindEvents();
        },
        _bindEvents: function (){
            var self = this;
            $('.slide-draggable').each(function (){
               self._addSlideDragAndDropHandlers($(this));
            });
            $('.section-draggable').each(function (){
                self._addSectionDragAndDropHandlers($(this));
            });
            $('.course-section').each(function (){
                self._addDropSlideOnSectionHandler($(this));
            });
        },
        _unbind: function (className){
            $("."+className).each(function (){
                $(this).unbind();
            });
        },
        _unbindAll: function (){
            this._unbind('slide-draggable');
            this._unbind('section-draggable');
            this._unbind('course-section');
        },
        _getSlides: function (){
            var self = this;
            var slides = $('li.content-slide');
            for(var i = 0; i < slides.length;i++){
                var slide = $(slides[i]);
                self.slides.push({
                    id: parseInt(slide.attr('slide_id')),
                    category_id: parseInt(slide.attr('category_id')),
                    sequence: i
                });
            }
        },
        _getCategories: function (){
            var self = this;
            self.categories = [];
            var categories = $('.course-section');
            for (var i = 0; i < categories.length;i++){
                var category = $(categories[i]);
                self.categories.push(parseInt(category.attr('category_id')));
            }
        },
        _addDropSlideOnSectionHandler: function (target){
            var self = this;
            target.on('drop', function (ev){
                if (ev.preventDefault){
                    ev.preventDefault();
                }
                self.dropTarget = $(ev.currentTarget);
                self.draggedElement[0].parentNode.removeChild(self.draggedElement[0]);
                $('ul[category_id='+target.attr('category_id')+']').append(self.draggedElement)
                self._addSlideDragAndDropHandlers(self.draggedElement);
                self._reorderSlides();
            });
            target.on('dragover', function (ev){
                if(ev.preventDefault){
                    ev.preventDefault();
                }
            });
        },
        _addSlideDragAndDropHandlers: function (target){
            var self = this;
            target.on('dragstart', function (ev){
                $('.section-draggable').removeClass('hold')
                self._unbind('section-draggable');
                ev.originalEvent.dataTransfer.effectAllowed = 'move';
                ev.originalEvent.dataTransfer.setData('text/html', this.outerHTML);
                self.draggedElement = target;
                self.draggedElement.addClass('hold');
            });
            target.on('dragover', function (ev){
                if ($(ev.currentTarget) !== self.draggedElement){
                    if (ev.preventDefault){
                        ev.preventDefault();
                    }
                    target.addClass('slide-hovered');
                }
            });
            target.on('dragleave', function (ev){
                if (ev.preventDefault){
                    ev.preventDefault();
                }
                target.removeClass('slide-hovered');
            });
            target.on('drop', function (ev){
                if (self.draggedElement.hasClass('slide-draggable') && target.hasClass('slide-draggable')){
                    if (ev.preventDefault){
                        ev.preventDefault();
                    }
                    target.removeClass('slide-hovered');
                    target.removeClass('hold');
                    if (target !== self.draggedElement){
                        self.dropTarget = $(ev.currentTarget);
                        self.draggedElement[0].parentNode.removeChild(self.draggedElement[0]);
                        var dropHTML = ev.originalEvent.dataTransfer.getData('text/html');
                        target[0].insertAdjacentHTML('beforebegin',dropHTML);
                        self.draggedElement = $(target[0].previousSibling);
                        self._reorderSlides();
                    }
                    self._unbindAll();
                    self._bindEvents();
                }
            });
            target.on('dragend', function (ev){
                if (ev.preventDefault){
                    ev.preventDefault();
                }
                target.removeClass('slide-hovered');
                target.removeClass('hold');
            });
        },
        _addSectionDragAndDropHandlers: function(target){
            var self = this;
            target.on('dragstart', function (ev){
                self._unbind('slide-draggable');
                self._unbind('course-section');
                ev.originalEvent.dataTransfer.effectAllowed = 'move';
                ev.originalEvent.dataTransfer.setData('text/html', this.outerHTML);
                self.draggedElement = target;
                self.draggedElement.addClass('hold');
            });
            target.on('dragover', function (ev){
                if (target.hasClass('section-draggable') && self.draggedElement.hasClass('section-draggable')){
                    if (ev.preventDefault){
                        ev.preventDefault();
                    }
                    target.addClass('slide-hovered');
                }
            });
            target.on('dragleave', function (ev){
                if (ev.preventDefault){
                    ev.preventDefault();
                }
                target.removeClass('slide-hovered');
            });
            target.on('drop', function (ev){
                if(ev.preventDefault){
                    ev.preventDefault();
                }
                if(self.draggedElement.hasClass('section-draggable')  && target.hasClass('section-draggable')){
                    target.removeClass('slide-hovered');
                    target.removeClass('hold');
                    self.dropTarget = $(ev.currentTarget);
                    if(target !== self.draggedElement && $(ev.currentTarget).hasClass('section-draggable')){
                        self.draggedElement[0].parentNode.removeChild(self.draggedElement[0]);
                        var dropHTML = ev.originalEvent.dataTransfer.getData('text/html');
                        target[0].insertAdjacentHTML('beforebegin',dropHTML);
                        self.draggedElement = $(target[0].previousSibling);
                        self._reorderCategories();
                        self._reorderSlides();
                        self._rebindUploadButton(self.draggedElement.attr('category_id'));
                    }
                    self._unbindAll();
                    self._bindEvents();
                }
            });
            target.on('dragend', function (ev){
                if (ev.preventDefault){
                    ev.preventDefault();
                }
                target.removeClass('slide-hovered');
                target.removeClass('hold');
            });
        },
        _reorderCategories: function (){
            var self = this;
            self._getCategories();
            self._rpc({
                route: '/web/dataset/resequence',
                params: {
                    model: "slide.category",
                    ids: self.categories
                }
            }).then(function (){
                self._resetCategoriesIndex();
            });
        },
        _resetCategoriesIndex: function (){
            var categoriesIndexes = $('.section-index')
            for (var i = 0; i < categoriesIndexes.length; i++){
                $(categoriesIndexes[i]).text(i+1)
            }
        },
        _reorderSlides: function(){
            var self = this;
            // In case the slide was transfered to another section
            if (self.draggedElement.hasClass('slide-draggable')){
                self.draggedElement.attr('category_id', parseInt(self.dropTarget.attr('category_id')))
            }
            self.slides = [];
            self._getSlides();
            self._rpc({
                route: "/slides/resequence_slides",
                params: {
                    slides_data: self.slides
                }
            }).then(function(){
            });
        },
        _rebindUploadButton: function(categoryID){
            var self = this;
            this.$('.oe_slide_js_upload[data-category-id='+categoryID+']').click(function(ev){
                ev.preventDefault();
                var data = $(ev.currentTarget).data();
                var dialog = new SlideUpload.SlideUploadDialog(self, data);
                dialog.appendTo(document.body);
                dialog.open();
            })
        }
    })

    publicWidget.registry.websiteSlidesCourseSlidesList = publicWidget.Widget.extend({
        selector: '.oe_js_course_slides_list',
        xmlDependencies: ['/website_slides/static/src/xml/website_slides_upload.xml'],
        init: function (el){
            this._super.apply(this, arguments);
        },
        start: function (){
            this._super.apply(this, arguments);
            var list = new List(this);
            list.appendTo(".oe_js_course_slides_list");
        }
    });
});
