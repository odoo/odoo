odoo.define('website_rating_project.rating', function (require) {
'use strict';

  var time = require('web.time');
  require('web.dom_ready');

  if(!$('.o_portal_project_rating').length) {
      return $.Deferred().reject("DOM doesn't contain '.o_portal_project_rating'");
  }

  /**
   * Rating popover with some informations
   */
  $('.o_portal_project_rating .o_rating_image').popover({
      placement: 'bottom',
      trigger: 'hover',
      html: 'true',
      content: function () {
          var id = $(this).data('id');
          var rating_date = $(this).data('rating-date');
          var base_date = time.auto_str_to_date(rating_date);
          var duration = moment(base_date).fromNow();
          $("#rating_"+ id).find(".rating_timeduration").text(duration);
          return $("#rating_"+ id).html();
      }
  });
});
