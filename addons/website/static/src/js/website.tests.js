var tests = {};
var droptest = function () {
  var errors = [];
  for (var snippet_id in tests) {
    if (!tests[snippet_id]['activated'] || !tests[snippet_id]['dropped']){
      console.log("Can't dropped or activated snippet: " + snippet_id);
    }
  }
  if (errors.length) {
      console.log(tests);
      throw new Error("Can't dropped or activated at least one snippet");
  }
  $("#oe_snippets").off('snippet-activated snippet-dropped');
};
var droptesttime = setTimeout(droptest,0);

$("#oe_snippets").off('snippet-activated snippet-dropped')
  .on('snippet-activated', function (event, dom) {
    tests[$(dom).data('src-snippet-id')]['activated'] = true;
    clearTimeout(droptesttime);
    droptesttime = setTimeout(droptest,0);
  })
  .on('snippet-dropped', function (event, dom, src_snipped_id) {
    tests[$(dom).data('src-snippet-id')]['dropped'] = true;
    clearTimeout(droptesttime);
    droptesttime = setTimeout(droptest,0);
  });
var $thumbnails = $('#oe_snippets div.oe_snippet[data-snippet-id] .oe_snippet_thumbnail');
$thumbnails.each(function () {
  var $thumbnail = $(this);
  tests[$thumbnail.parent().data('snippet-id')] = {};
  var position = $thumbnail.position();
  $thumbnail.trigger( $.Event( "mousedown", { which: 1, pageX: position.left, pageY: position.top } ) );
  $thumbnail.trigger( $.Event( "mousemove", { which: 1, pageX: position.left+100, pageY: position.top+100 } ) );
  $first_drop = $(".oe_drop_zone").first();
  position = $first_drop.position();
  $first_drop.trigger( $.Event( "mouseup", { which: 1, pageX: position.left+20, pageY: position.top+20 } ) );
  clearTimeout(droptesttime);
  droptesttime = setTimeout(droptest,0);
});
