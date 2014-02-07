//global vars.
var disqus_identifier;
var disqus_url;

(function($) {

    var settings = {};

    $.fn.extend({
    inlineDisqussions: function(options) {

      // Set up defaults
      var defaults = {
        identifier: 'name',
        position: 'right',
        background: 'white',
        maxWidth: 9999
      };

      // Overwrite default options with user provided ones.
      settings = $.extend({}, defaults, options);

      // Append #disqus_thread to body if it doesn't exist yet.
      if ($('#disqussions_wrapper').length === 0) {
        $('<div id="disqussions_wrapper"></div>').appendTo($('body'));
      }
      if ($('#disqus_thread').length === 0) {
        $('<div id="disqus_thread"></div>').appendTo('#disqussions_wrapper');
      }
      else {
        mainThreadHandler();
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
    // Create the discussion note.
    var a = $('<a class="disqussion-link" />')
      .attr('href', window.location.pathname + settings.identifier + '-'  + i + '#comment')
      .attr('data-disqus-identifier', identifier)
      .attr('data-disqus-url', window.location.href + settings.identifier + '-' + i)
      .attr('data-disqus-position', settings.position)
      .text('+')
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

    // Load the relative discussion.
    a.delegate('a.disqussion-link', "click", function(e) {
      e.preventDefault();

      if ($(this).is('.active')) {
        e.stopPropagation();
        hideDisqussion();
      }
      else {
        loadDisqus($(this), function(source) {
        });
      }
    });
  };

  var mainThreadHandler = function() {

    // Create the discussion note.
    if ($('a.main-disqussion-link').length === 0) {

      var a = $('<a class="main-disqussion-link" />')
        .attr('href', window.location.pathname + '#disqus_thread')
        .text('Comments')
        .wrap('<h2 class="main-disqussion-link-wrp" />')
        .parent()
        .insertBefore('#disqus_thread');

      // Load the relative discussion.
      a.delegate('a.main-disqussion-link', "click", function(e) {
        e.preventDefault();

        if ($(this).is('.active')) {
          e.stopPropagation();
        }
        else {
          loadDisqus($(this), function(source) {
          });
        }
      });
    }
  };

  var loadDisqus = function(source, callback) {

    var identifier = source.attr('data-disqus-identifier');
    var url = source.attr('data-disqus-url');
    var body = $(document.body).find('h1')
    var id = body.attr('data-oe-id');
      disqus_identifier = identifier;
      disqus_url = url;
      
      var comment = '';
      openerp.jsonRpc("/blog_post/comments/", 'call', {
          'blog': id,
          'tag_id':identifier,
      })
      .then(function (data) {
          if(!data)
              return;
          _.map(data, function(res){
        	 comment += '<li class="media">\
                  <div class="media-body">\
                      <img class="media-object pull-left img-circle" src="'+ res.author_image + '" style="width: 30px; margin-right: 5px;"/>\
                      <div class="media-body">\
                          <h5 class="media-heading">\
                              <span>'+res.author_name+'</span> <small>on <span>'+res.date+'</span></small>\
                          </h5>\
                      </div>\
                  </div>\
              </li><li><small class="text-muted">'+res.body+'</small></li><hr/>'
          });
          $('.content').html('<ul class="media-list">'+comment+'</ul>')
      });
      
      $('a[data-disqus-identifier="'+identifier+'"]').append('<div class="mycontent hidden"><form id="comment" action="/blogpost/comment" method="POST"><input name="tag_id" value="'+ identifier +'" type="hidden"/><input name="blog_post_id" value="'+id+'" type="hidden"/><textarea rows="3" id="comment" name="comment" placeholder="Write a comment..."/><br/><button id="submit" type="submit" class="btn btn-primary btn-xs mb8 mt4">Post</button></form><div class="content"/></div>')
      
//       $('#submit').click(function() {
//    	  console.log('aaaaaa',$('p[data-disqus-identifier="'+identifier+'"]'))
//    	  $('p[data-disqus-identifier="'+identifier+'"]').attr('data-count','2');
//    	  debugger;
//      });
      $('a[data-disqus-identifier="'+identifier+'"]').popover({
          html:true,
          placement:'right',
          content:function(){
              return $($(this).data('contentwrapper')).html();
          }
      });
     
    // Add 'active' class.
    $('a.disqussion-link, a.main-disqussion-link').removeClass('active').filter(source).addClass('active');
    $('a[data-disqus-identifier="'+identifier+'"]').popover('hide').filter(source).popover('show');
    callback(source);
  };
  
  var hideDisqussion = function() {
      $('a[data-disqus-identifier="'+disqus_identifier+'"]').popover('hide')
      $('a.disqussion-link').removeClass('active');
  };

})(jQuery);

$(document).ready(function() {
    $("#blog_content p").inlineDisqussions();
});
 