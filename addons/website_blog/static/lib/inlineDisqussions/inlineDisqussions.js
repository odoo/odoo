//global vars.
var disqus_identifier;

(function($) {
    var settings = {};
    $.fn.extend({
        inlineDisqussions: function(options) {
        // Set up defaults
            var defaults = {
                identifier: 'name',
                position: 'right',
                post_id: $('h1').attr('data-oe-id'),
            };

            // Overwrite default options with user provided ones.
            settings = $.extend({}, defaults, options);

            // Append #disqus_thread to body if it doesn't exist yet.
            if ($('#disqussions_wrapper').length === 0) {
                $('<div id="disqussions_wrapper"></div>').appendTo($('body'));
            }

            // Attach a discussion to each paragraph.
            $(this).each(function(i) {
                disqussionNotesHandler(i, $(this));
            });

            // Hide the discussion.
            $('html').click(function(event) {
                if($(event.target).parents('#disqussions_wrapper, .main-disqussion-link-wrp').length === 0) {
                    hideDisqussion();
                    }
            });
        }
    });

    var disqussionNotesHandler = function(i, node) {

        var identifier;
        // You can force a specific identifier by adding an attribute to the paragraph.
        if (node.attr('data-disqus-identifier')) {
            identifier = node.attr('data-disqus-identifier');
        }
        else {
            while ($('[data-disqus-identifier="' + settings.identifier + '-' + i + '"]').length > 0) {
                i++;
            }
            identifier = settings.identifier + '-' + i;
        }
        openerp.jsonRpc("/blogpost/discussion/", 'call', {
            'post_id': settings.post_id,
            'discussion':identifier,
        }).then(function(data){
            prepareDisquseLink(data,identifier,node);
        });
    };

    var prepareDisquseLink = function(data,identifier,node) {

        var a = $('<a class="disqussion-link" />')
            .attr('data-disqus-identifier', identifier)
            .attr('data-disqus-position', settings.position)
            .text(data.length > 0 ? data.length : '+')
            .attr('data-contentwrapper','.mycontent')
            .wrap('<div class="disqussion" />')
            .parent()
            .appendTo('#disqussions_wrapper');
            a.css({
                'top': node.offset().top,
                'left': settings.position == 'right' ? node.offset().left + node.outerWidth() : node.offset().left - a.outerWidth()
            });

        node.attr('data-disqus-identifier', identifier).mouseover(function() {
            a.addClass("hovered");
        }).mouseout(function() {
            a.removeClass("hovered");
        });

        a.delegate('a.disqussion-link', "click", function(e) {
            e.preventDefault();
            if ($(this).is('.active')) {
                e.stopPropagation();
                hideDisqussion();
            }
            else {
                loadDisqus(data, $(this), function(source) {});
            }
        });
    };

    var loadDisqus = function(data, source, callback) {
        var identifier = source.attr('data-disqus-identifier');
        $('a[data-disqus-identifier="'+disqus_identifier+'"]').popover('destroy')
        disqus_identifier = identifier;
        var elt = $('a[data-disqus-identifier="'+identifier+'"]');
        elt.append('\
            <div class="mycontent hidden">\
                <form id="comment" action="/blogpost/comment" method="POST">\
                    <input name="discussion" value="'+ identifier +'" type="hidden"/>\
                    <input name="blog_post_id" value="'+ settings.post_id +'" type="hidden"/>\
                    <textarea class="mb8 form-control" rows="2" name="comment" placeholder="Write a comment..."/>\
                    <button id="submit" type="submit" class="btn btn-primary btn-xs mb8 mt4">Post</button>\
                </form>\
                <div class="discussion_history"/>\
            </div>')
        var comment = '';
        _.each(data, function(res){
            comment += '<li class="media">\
                <div class="media-body">\
                    <img class="media-object pull-left img-circle" src="'+ res.author_image + '" style="width: 30px; margin-right: 5px;"/>\
                    <div class="media-body">\
                        <h5 class="media-heading">\
                            <small><span>'+res.author_name+'</span> on <span>'+res.date+'</span></small>\
                        </h5>\
                    </div>\
                </div>\
            </li><li><h6>'+res.body+'</h6></li><hr/>'
        });
        $('.discussion_history').html('<ul class="media-list">'+comment+'</ul>');
        createPopOver(elt);

        // Add 'active' class.
        $('a.disqussion-link, a.main-disqussion-link').removeClass('active').filter(source).addClass('active');
        elt.popover('hide').filter(source).popover('show');
        callback(source);
    };

    var createPopOver = function (elt) {
        elt.popover({
            placement:'right', 
            trigger:'manual',
            html:true, content:function(){
                return $($(this).data('contentwrapper')).html();
            }
        });
    };

    var hideDisqussion = function() {
        $('a[data-disqus-identifier="'+disqus_identifier+'"]').popover('destroy');
        $('a.disqussion-link').removeClass('active');
    };
  
})(jQuery);
