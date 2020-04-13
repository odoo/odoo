(function(){
    $.fn.share = function(options) {
        var option = $.extend($.fn.share.defaults,options);
        var selected_text ="";
        $.extend($.fn.share,{
            init : function(shareable) {
                var self = this;
                $.fn.share.defaults.shareable = shareable;
                $.fn.share.defaults.shareable.on('mouseup',function(){
                    if ($(this).parents('body.editor_enable').length === 0) {
                        self.popOver();
                    }
                });
                $.fn.share.defaults.shareable.on('mousedown',function(){
                    self.destroy();
                });
            },
            getContent : function() {
                var popover_content = '';
                if($('.blog_title, .blog_content').hasClass('js_comment')){
                    selected_text = this.getSelection('string');
                    popover_content += '<a class="o_share_comment mr12"><i class="fa fa-comment fa-lg mr4 ml4"/></a>';
                }
                if($('.blog_title, .blog_content').hasClass('js_tweet')){
                    var tweet = '"%s" - %s';
                    var baseLength = tweet.replace(/%s/g, '').length;
                    // Shorten the selected text to match the tweet max length
                    // Note: all (non-localhost) urls in a tweet have 23 characters https://support.twitter.com/articles/78124
                    var selectedText = this.getSelection('string').substring(0, option.maxLength - baseLength - 23);
                    var text = btoa(encodeURIComponent(_.str.sprintf(tweet, selectedText, window.location.href)));
                    popover_content += _.str.sprintf(
                        "<a onclick=\"window.open('%s' + atob('%s'), '_%s','location=yes,height=570,width=520,scrollbars=yes,status=yes')\"><i class=\"ml4 mr4 fa fa-twitter fa-lg\"/></a>",
                        option.shareLink, text, option.target);
                }
                return popover_content;
            },
            commentEdition : function(){
                var positionComment = ($('#comments').position()).top-50;
                $(".o_portal_chatter_composer_form textarea").val('"' + selected_text + '" ').focus();
                $('html, body').stop().animate({
                    'scrollTop': positionComment
                }, 500, 'swing', function () {
                    window.location.hash = 'blog_post_comment_quote';
                });
            },
            getSelection : function(share) {
                if(window.getSelection){
                    var selection = window.getSelection();
                    if (!selection || selection.rangeCount === 0) {
                        return "";
                    }
                    if (share === 'string') {
                        return String(selection.getRangeAt(0)).replace(/\s{2,}/g, ' ');
                    } else {
                        return selection.getRangeAt(0);
                    }
                }
                else if(document.selection){
                    if (share === 'string') {
                        return document.selection.createRange().text.replace(/\s{2,}/g, ' ');
                    } else {
                        return document.selection.createRange();
                    }
                }
            },
            popOver : function() {
                this.destroy();
                if(this.getSelection('string').length < option.minLength)
                    return;
                var data = this.getContent();
                var range = this.getSelection();

                var newNode = document.createElement("span");
                range.insertNode(newNode);
                newNode.className = option.className;
                var $pop = $(newNode);
                $pop.popover({
                    trigger:'manual',
                    placement: option.placement,
                    html: true,
                    content: function(){
                        return data;
                    }
                }).popover('show');
                $('.o_share_comment').on('click', this.commentEdition);
            },
            destroy : function(){
                var $span = $('span.'+option.className);
                $span.popover('hide');
                $span.remove();
            }
        });
        $.fn.share.init(this);
    };

    $.fn.share.defaults = {
        shareLink : "http://twitter.com/intent/tweet?text=",
        minLength  : 5,
        maxLength  : 140,
        target     : "blank",
        className  : "share",
        placement  : "top",
    };

}());
