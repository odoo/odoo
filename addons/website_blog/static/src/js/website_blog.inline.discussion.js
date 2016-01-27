odoo.define('website_blog.InlineDiscussion', function (require) {
'use strict';

// Inspired from https://github.com/tsi/inlineDisqussions

var ajax = require('web.ajax');
var core = require('web.core');
var base = require('web_editor.base');
var qweb = core.qweb;


var InlineDiscussion = core.Class.extend({
    init: function(options) {
        var defaults = {
            position: 'right',
            post_id: $('#blog_post_name').attr('data-blog-id'),
            content : false,
            public_user: false,
        };
        this.settings = $.extend({}, defaults, options);
    },
    start: function() {
        var self = this;
        var $wrapper = $('#discussions_wrapper');
        if (!$wrapper.length && this.settings.content.length > 0) {
            $wrapper = $('<div id="discussions_wrapper"></div>').insertAfter($('#blog_content'));
        }
        // Attach a discussion to each paragraph.
        this.discussions_handler(this.settings.content);

        // Open/close the discussion.
        $('html').click(function (event) {
            var $target = $(event.target);
            var open;

            if ((!$target.is('.discussion-link:not(.active)') && !$target.closest('.popover').length) || !$target.closest('#discussions_wrapper').length) {
                self.hide_discussion();
                open = false;
            } else if ($target.is('.discussion-link')) {
                self.get_discussion($target);
                open = true;
            }

            if (open === !$wrapper.hasClass('o_move_discuss')) {
                $wrapper.toggleClass('o_move_discuss', open);
                $wrapper.animate({
                    'marginLeft': (open ? '-' : '+')+"=20%"
                });
                $('#blog_content[enable_chatter_discuss=True]').animate({
                    'marginLeft': (open ? '-' : '+')+"=40%"
                });
            }
        });
    },
    prepare_data : function(identifier, comment_count) {
        var self = this;
        return ajax.jsonRpc("/blog/post_get_discussion/", 'call', {
            'post_id': self.settings.post_id,
            'path': identifier,
            'count': comment_count, //if true only get length of total comment, display on discussion thread.
        });
    },
    prepare_multi_data : function(identifiers, comment_count) {
        var self = this;
        return ajax.jsonRpc("/blog/post_get_discussions/", 'call', {
            'post_id': self.settings.post_id,
            'paths': identifiers,
            'count': comment_count, //if true only get length of total comment, display on discussion thread.
        });
    },
    discussions_handler: function() {
        var self = this;
        var node_by_id = {};
        $(self.settings.content).each(function() {
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
    },
    get_discussion : function(source) {
        var self = this;
        var identifier = source.attr('data-discus-identifier');
        self.hide_discussion();
        self.discus_identifier = identifier;
        var elt = $('a[data-discus-identifier="'+identifier+'"]');
        self.settings.current_url = window.location;
        elt.append(qweb.render("website.blog_discussion.popover", {'identifier': identifier , 'options': self.settings}));
        var comment = '';
        self.prepare_data(identifier,false).then(function(data){
            _.each(data, function(res){
                comment += qweb.render("website.blog_discussion.comment", {'res': res});
            });
            $('.discussion_history').html('<ul class="media-list mt8">' + comment + '</ul>');
            self.create_popover(elt, identifier);
            // Add 'active' class.
            $('a.discussion-link, a.main-discussion-link').removeClass('active').filter(source).addClass('active');
            elt.popover('hide').filter(source).popover('show');
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
        if(!comment) {
            $('div#inline_comment').addClass('has-error');
            return false;
        }
        $("div#inline_comment").removeClass('has-error');
        $(".popover textarea#inline_comment").val('');
        return [comment];
    },
    post_discussion : function() {
        var self = this;
        var val = self.validate(self.settings.public_user);
        if(!val) return;
        ajax.jsonRpc("/blog/post_discussion", 'call', {
            'blog_post_id': self.settings.post_id,
            'path': self.discus_identifier,
            'comment': val[0],
        }).then(function(res){
            $(".popover ul.media-list").prepend(qweb.render("website.blog_discussion.comment", {'res': res[0]}));
            var ele = $('a[data-discus-identifier="'+ self.discus_identifier +'"]');
            ele.text(_.isNaN(parseInt(ele.text())) ? 1 : parseInt(ele.text())+1);
            ele.addClass('has-comments');
        });
    },
    hide_discussion : function() {
        var self =  this;
        $('a[data-discus-identifier="'+ self.discus_identifier+'"]').popover('destroy');
        $('a.discussion-link').removeClass('active');
    }

});

return InlineDiscussion;

});
