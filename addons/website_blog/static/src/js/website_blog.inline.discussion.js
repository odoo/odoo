// Inspired from https://github.com/tsi/inlinediscussions
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
                identifier: 'name',
                position: 'right',
                post_id: $('#blog_post_name').attr('data-oe-id'),
                document_user : false,
                content : false,
            };
            self.settings = $.extend({}, defaults, options);
            self.do_render(self);
        },
        do_render: function(data) {
            var self = this;
            if ($('#discussions_wrapper').length === 0) {
                $('<div id="discussions_wrapper"></div>').appendTo($('#blog_content'));
            }
            // Attach a discussion to each paragraph.
            $(self.settings.content).each(function(i) {
                self.discussion_handler(i, $(this));
            });
            // Hide the discussion.
            $('html').click(function(event) {
                if($(event.target).parents('#discussions_wrapper, .main-discussion-link-wrp').length === 0) {
                    self.hide_discussion();
                }
            });
        },
        prepare_data : function(identifier) {
            var self = this;
            return openerp.jsonRpc("/blogpost/get_discussion/", 'call', {
                'post_id': self.settings.post_id,
                'discussion':identifier,
            })
        },
        discussion_handler : function(i, node) {
            var self = this;
            var identifier;
            // You can force a specific identifier by adding an attribute to the paragraph.
            if (node.attr('data-discus-identifier')) {
                identifier = node.attr('data-discus-identifier');
            }
            else {
                while ($('[data-discus-identifier="' + self.settings.identifier + '-' + i + '"]').length > 0) {
                    i++;
                }
                identifier = self.settings.identifier + '-' + i;
            }
            self.prepare_data(identifier).then(function(data){
                self.prepare_discuss_link(data,identifier,node)
            });
        },
        prepare_discuss_link :  function(data, identifier, node) {
            var self = this;
            var cls = data.length > 0 ? 'discussion-link has-comments' : 'discussion-link';
            var a = $('<a class="'+ cls +' css_editable_mode_hidden" />')
                .attr('data-discus-identifier', identifier)
                .attr('data-discus-position', self.settings.position)
                .text(data.length > 0 ? data.length : '+')
                .attr('data-contentwrapper','.mycontent')
                .wrap('<div class="discussion" />')
                .parent()
                .appendTo('#discussions_wrapper');
            a.css({
                'top': node.offset().top,
                'left': self.settings.position == 'right' ? node.outerWidth() + node.offset().left: node.offset().left - a.outerWidth()
            });
            node.attr('data-discus-identifier', identifier).mouseover(function() {
                a.addClass("hovered");
            }).mouseout(function() {
                a.removeClass("hovered");
            });

            a.delegate('a.discussion-link', "click", function(e) {
                e.preventDefault();
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
            self.prepare_data(identifier).then(function(data){
                console.log(identifier, data);
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
        post_discussion : function(identifier) {
            var self = this;
            var val = $(".popover #comment").val()
            if(val){
                $(".popover #comment").removeClass('danger');
                openerp.jsonRpc("/blogpost/post_discussion", 'call', {
                    'blog_post_id': self.settings.post_id,
                    'discussion': self.discus_identifier,
                    'comment': val,
                }).then(function(res){
                    $(".popover ul.media-list").prepend(qweb.render("website.blog_discussion.comment", {'res': res}))
                    $(".popover #comment").val('')
                    var ele = $('a[data-discus-identifier="'+ self.discus_identifier +'"]');
                    ele.text(_.isNaN(parseInt(ele.text())) ? 1 : parseInt(ele.text())+1)
                });
            }
        },
        hide_discussion : function() {
            var self =  this;
            $('a[data-discus-identifier="'+ self.discus_identifier+'"]').popover('destroy');
            $('a.discussion-link').removeClass('active');
        }
        
    });

})();
