odoo.define('html_form_builder.front', function (require) {
'use strict';

$(function() {

  //Load the token via javascript since Odoo has issue with request.csrf_token() inside snippets
  $(".html_form input[name='csrf_token']").val(odoo.csrf_token);

});

});