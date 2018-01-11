// Inspired from https://github.com/tsi/inlineDisqussions
(function () {
    
    'use strict';
    
    var website = openerp.website,
    qweb = openerp.qweb;
    website.add_template_file('/website_blog/static/src/xml/website_blog.inline.discussion.xml');
    website.blog_discussion = openerp.Class.extend({
        init: function(options) {
            var self = this ;
            self.discus_identifier;
            var defaults = {
                position: 'right',
                post_id: $('#blog_post_name').attr('data-blog-id'),
                content : false,
                public_user: false,
            };
            self.settings = $.extend({}, defaults, options);
            self.do_render(self);
        },
        do_render: function(data) {
            var self = this;
            if ($('#discussions_wrapper').length === 0 && self.settings.content.length > 0) {
                $('<div id="discussions_wrapper"></div>').insertAfter($('#blog_content'));
            }
            // Attach a discussion to each paragraph.
            self.discussions_handler(self.settings.content);

            // Hide the discussion.
            $('html').click(function(event) {
                if($(event.target).parents('#discussions_wrapper, .main-discussion-link-wrp').length === 0) {
                    self.hide_discussion();
                }
                if(!$(event.target).hasClass('discussion-link') && !$(event.target).parents('.popover').length){
                    if($('.move_discuss').length){
                        $('[enable_chatter_discuss=True]').removeClass('move_discuss');
                        $('[enable_chatter_discuss=True]').animate({
                            'marginLeft': "+=40%"
                        });
                        $('#discussions_wrapper').animate({
                            'marginLeft': "+=250px"
                        });
                    }
                }
            });
        },
        prepare_data : function(identifier, comment_count) {
            var self = this;
            return openerp.jsonRpc("/blogpost/get_discussion/", 'call', {
                'post_id': self.settings.post_id,
                'path': identifier,
                'count': comment_count, //if true only get length of total comment, display on discussion thread.
            })
        },
        prepare_multi_data : function(identifiers, comment_count) {
            var self = this;
            return openerp.jsonRpc("/blogpost/get_discussions/", 'call', {
                'post_id': self.settings.post_id,
                'paths': identifiers,
                'count': comment_count, //if true only get length of total comment, display on discussion thread.
            })
        },
        discussions_handler: function() {
            var self = this;
            var node_by_id = {};
            $(self.settings.content).each(function(i) {
                var node = $(this);
                var identifier = node.attr('data-chatter-id');
                if (identifier) {
                    node_by_id[identifier] = node;
                }
            });
            self.prepare_multi_data(_.keys(node_by_id), true).then( function (multi_data) {
                _.forEach(multi_data, function(data) {
                    self.prepare_discuss_link(data.val, data.path, node_by_id[data.path]);
                });
            });
        },
        prepare_discuss_link :  function(data, identifier, node) {
            var self = this;
            var cls = data > 0 ? 'discussion-link has-comments' : 'discussion-link';
            var a = $('<a class="'+ cls +' css_editable_mode_hidden" />')
                .attr('data-discus-identifier', identifier)
                .attr('data-discus-position', self.settings.position)
                .text(data > 0 ? data : '+')
                .attr('data-contentwrapper', '.mycontent')
                .wrap('<div class="discussion" />')
                .parent()
                .appendTo('#discussions_wrapper');
            a.css({
                'top': node.offset().top,
                'left': self.settings.position == 'right' ? node.outerWidth() + node.offset().left: node.offset().left - a.outerWidth()
            });
            // node.attr('data-discus-identifier', identifier)
            node.mouseover(function() {
                a.addClass("hovered");
            }).mouseout(function() {
                a.removeClass("hovered");
            });

            a.delegate('a.discussion-link', "click", function(e) {
                e.preventDefault();
                if(!$('.move_discuss').length){
                    $('[enable_chatter_discuss=True]').addClass('move_discuss');
                    $('[enable_chatter_discuss=True]').animate({
                        'marginLeft': "-=40%"
                    });
                    $('#discussions_wrapper').animate({
                        'marginLeft': "-=250px"
                    });
                }
                if ($(this).is('.active')) {
                    e.stopPropagation();
                    self.hide_discussion();
                }
                else {
                    self.get_discussion($(this), function(source) {});
                }
            });
        },
        get_discussion : function(source, callback) {
            var self = this;
            var identifier = source.attr('data-discus-identifier');
            self.hide_discussion();
            self.discus_identifier = identifier;
            var elt = $('a[data-discus-identifier="'+identifier+'"]');
            elt.append(qweb.render("website.blog_discussion.popover", {'identifier': identifier , 'options': self.settings}));
            var comment = '';
            self.prepare_data(identifier,false).then(function(data){
                _.each(data, function(res){
                    comment += qweb.render("website.blog_discussion.comment", {'res': res});
                });
                $('.discussion_history').html('<ul class="media-list">'+comment+'</ul>');
                self.create_popover(elt, identifier); 
                // Add 'active' class.
                $('a.discussion-link, a.main-discussion-link').removeClass('active').filter(source).addClass('active');
                elt.popover('hide').filter(source).popover('show');
                callback(source);
            });
        },
        create_popover : function(elt, identifier) {
            var self = this;
            elt.popover({
                placement:'right',
                trigger:'manual',
                html:true, content:function(){
                    return $($(this).data('contentwrapper')).html();
                }
            }).parent().delegate(self).on('click','button#comment_post',function(e) {
                e.stopImmediatePropagation();
                self.post_discussion(identifier);
            });
        },
        validate : function(public_user){
            var comment = $(".popover textarea#inline_comment").val();
            if (public_user){
                var author_name = $('.popover input#author_name').val();
                var author_email = $('.popover input#author_email').val();
                if(!comment || !author_name || !author_email){
                    if (!author_name) 
                        $('div#author_name').addClass('has-error');
                    else 
                        $('div#author_name').removeClass('has-error');
                    if (!author_email)
                        $('div#author_email').addClass('has-error');
                    else
                        $('div#author_email').removeClass('has-error');
                    if(!comment)
                        $('div#inline_comment').addClass('has-error');
                    else
                        $('div#inline_comment').removeClass('has-error');
                    return false
                }
            }
            else if(!comment) {
                $('div#inline_comment').addClass('has-error');
                return false
            }
            $("div#inline_comment").removeClass('has-error');
            $('div#author_name').removeClass('has-error');
            $('div#author_email').removeClass('has-error');
            $(".popover textarea#inline_comment").val('');
            $('.popover input#author_name').val('');
            $('.popover input#author_email').val('');
            return [comment, author_name, author_email]
        },
        post_discussion : function(identifier) {
            var self = this;
            var val = self.validate(self.settings.public_user)
            if(!val) return
            openerp.jsonRpc("/blogpost/post_discussion", 'call', {
                'blog_post_id': self.settings.post_id,
                'path': self.discus_identifier,
                'comment': val[0],
                'name' : val[1],
                'email': val[2],
            }).then(function(res){
                $(".popover ul.media-list").prepend(qweb.render("website.blog_discussion.comment", {'res': res[0]}))
                var ele = $('a[data-discus-identifier="'+ self.discus_identifier +'"]');
                ele.text(_.isNaN(parseInt(ele.text())) ? 1 : parseInt(ele.text())+1)
                ele.addClass('has-comments');
            });
        },
        hide_discussion : function() {
            var self =  this;
            $('a[data-discus-identifier="'+ self.discus_identifier+'"]').popover('destroy');
            $('a.discussion-link').removeClass('active');
        }
        
    });

})();
