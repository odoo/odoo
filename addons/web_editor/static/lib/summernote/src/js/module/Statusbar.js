define([
  'summernote/core/dom'
], function (dom) {
  var EDITABLE_PADDING = 24;

  var Statusbar = function () {
    var $document = $(document);

    this.attach = function (layoutInfo, options) {
      if (!options.disableResizeEditor) {
        layoutInfo.statusbar().on('mousedown', hStatusbarMousedown);
      }
    };

    /**
     * `mousedown` event handler on statusbar
     *
     * @param {MouseEvent} event
     */
    var hStatusbarMousedown = function (event) {
      event.preventDefault();
      event.stopPropagation();

      var $editable = dom.makeLayoutInfo(event.target).editable();
      var editableTop = $editable.offset().top - $document.scrollTop();

      var layoutInfo = dom.makeLayoutInfo(event.currentTarget || event.target);
      var options = layoutInfo.editor().data('options');

      $document.on('mousemove', function (event) {
        var nHeight = event.clientY - (editableTop + EDITABLE_PADDING);

        nHeight = (options.minHeight > 0) ? Math.max(nHeight, options.minHeight) : nHeight;
        nHeight = (options.maxHeight > 0) ? Math.min(nHeight, options.maxHeight) : nHeight;

        $editable.height(nHeight);
      }).one('mouseup', function () {
        $document.off('mousemove');
      });
    };
  };

  return Statusbar;
});
