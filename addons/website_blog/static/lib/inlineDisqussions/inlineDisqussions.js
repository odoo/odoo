// Disqus global vars.
var disqus_identifier;
var disqus_url;

(function($) {
	
    jQuery(document).ready(function() {
        jQuery("main p").inlineDisqussions();
    });
     
    var settings = {};

    $.fn.extend({
    inlineDisqussions: function(options) {

      // Set up defaults
      var defaults = {
        identifier: 'name',
        displayCount: true,
        highlighted: false,
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

      // Display comments count.
      if (settings.displayCount) {
       // loadDisqusCounter();
      }

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
      
      var self = this;
      var p = '';
      openerp.jsonRpc("/blog_post/comments/", 'call', {
          'blog': id,
          'tag_id':identifier,
      })
      .then(function (data) {
          if(!data)
              return;
          _.map(data, function(res){
              p += '<div><img class="img-circle oe_inline" style="width: 25%; margin-right:10px;" src="' + res.author_image + '"/><h5 class="media-heading"><span>'+res.author_name+'</span><small> on <span>'+res.date+'</span></small></h5><span>'+res.body+'</span></div>'
          });
          $('.content').html(p)
      });

      $('#disqussions_wrapper').append('<div class="mycontent hidden"><form id="comment" action="/blogpost/comment" method="POST"><input name="tag_id" value="'+ identifier +'" type="hidden"/><input name="blog_post_id" value="'+id+'" type="hidden"/><textarea class="form-control" rows="3" id="comment" name="comment" placeholder="Write a comment..."/><br/><button id="submit" type="submit" class="btn btn-primary mt8">Post</button></form><div class="content"/></div>')

      $('.disqussion-link').popover({
          html:true,
          placement:'right',
          content:function(){
              return $($(this).data('contentwrapper')).html();
          }
      });
//      $('#submit').click(function() {
//    	  $('p[data-disqus-identifier="'+identifier+'"]').attr('data-count','2');
//    	  debugger;
//      });
      
    // Add 'active' class.
    $('a.disqussion-link, a.main-disqussion-link').removeClass('active').filter(source).addClass('active');
    callback(source);

  };

//  var loadDisqusCounter = function() {
//
//    // Append the Disqus count script to <head>.
//    var s = document.createElement('script'); s.type = 'text/javascript'; s.async = true;
//    s.src = '//' + disqus_shortname + '.disqus.com/count.js';
//    $('head').append(s);
//
//    // Add class to discussions that already have comments.
//    window.setTimeout(function() {
//      $('.disqussion-link').filter(function() {
//        return $(this).text().match(/[1-9]/g);
//      }).addClass("has-comments");
//    }, 1000);
//
//  };

  var hideDisqussion = function() {
    
    $('.disqussion-link').popover('hide')
    $('a.disqussion-link').removeClass('active');
  
  };

})(jQuery);
