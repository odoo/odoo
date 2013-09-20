/*! http://mths.be/smoothscroll v1.5.2 by @mathias */
;
(function(document, $) {

  var $scrollElement = (function() {
    // Find out what to scroll (html or body)
    var $html = $(document.documentElement),
      $body = $(document.body),
      bodyScrollTop;
    if ($html.scrollTop()) {
      return $html;
    } else {
      bodyScrollTop = $body.scrollTop();
      // If scrolling the body doesn’t do anything
      if ($body.scrollTop(bodyScrollTop + 1).scrollTop() == bodyScrollTop) {
        return $html;
      } else {
        // We actually scrolled, so undo it
        return $body.scrollTop(bodyScrollTop);
      }
    }
  }());

  $.fn.smoothScroll = function(speed) {
    speed = ~~speed || 400;
    // Look for links to anchors (on any page)
    return this.find('a[href*="#"]').click(function(event) {
      var hash = this.hash,
        $hash = $(hash); // The in-document element the link points to
      // If it’s a link to an anchor in the same document
      if (location.pathname.replace(/^\//, '') === this.pathname.replace(/^\//, '') && location.hostname === this.hostname) {
        // If the anchor actually exists…
        if ($hash.length) {
          // …don’t jump to the link right away…
          event.preventDefault();
          // …and smoothly scroll to it
          $scrollElement.stop().animate({
            'scrollTop': $hash.offset().top
          }, speed, function() {
            location.hash = hash;
          });
        }
      }
    }).end();
  };

}(document, jQuery));