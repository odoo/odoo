define([
  'summernote/core/func',
  'summernote/core/list',
  'summernote/module/Button'
], function (func, list, Button) {
  /**
   * @class module.Popover
   *
   * Popover (http://getbootstrap.com/javascript/#popovers)
   *
   */
  var Popover = function () {
    var button = new Button();

    this.button = button; // ODOO: allow access for override

    /**
     * returns position from placeholder
     *
     * @private
     * @param {Node} placeholder
     * @param {Object} options
     * @param {Boolean} options.isAirMode
     * @return {Position}
     */
    var posFromPlaceholder = function (placeholder, options) {
      var isAirMode = options && options.isAirMode;
      var isLeftTop = options && options.isLeftTop;

      var $placeholder = $(placeholder);
      var pos = isAirMode ? $placeholder.offset() : $placeholder.position();
      var height = isLeftTop ? 0 : $placeholder.outerHeight(true); // include margin

      // popover below placeholder.
      return {
        left: pos.left,
        top: pos.top + height
      };
    };

    /**
     * show popover
     *
     * @private
     * @param {jQuery} popover
     * @param {Position} pos
     */
    var showPopover = function ($popover, pos) {
      $popover.css({
        display: 'block',
        left: pos.left,
        top: pos.top
      });
    };

    var PX_POPOVER_ARROW_OFFSET_X = 20;

    /**
     * update current state
     * @param {jQuery} $popover - popover container
     * @param {Object} styleInfo - style object
     * @param {Boolean} isAirMode
     */
    this.update = function ($popover, styleInfo, isAirMode) {
      button.update($popover, styleInfo);

      var $linkPopover = $popover.find('.note-link-popover');
      if (styleInfo.anchor) {
        var $anchor = $linkPopover.find('a');
        var href = $(styleInfo.anchor).attr('href');
        var target = $(styleInfo.anchor).attr('target');
        $anchor.attr('href', href).text(href);
        if (!target) {
          $anchor.removeAttr('target');
        } else {
          $anchor.attr('target', '_blank');
        }
        showPopover($linkPopover, posFromPlaceholder(styleInfo.anchor, {
          isAirMode: isAirMode
        }));
      } else {
        $linkPopover.hide();
      }

      var $imagePopover = $popover.find('.note-image-popover');
      if (styleInfo.image) {
        showPopover($imagePopover, posFromPlaceholder(styleInfo.image, {
          isAirMode: isAirMode,
          isLeftTop: true
        }));
      } else {
        $imagePopover.hide();
      }

      var $airPopover = $popover.find('.note-air-popover');
      if (isAirMode && styleInfo.range && !styleInfo.range.isCollapsed()) {
        var rect = list.last(styleInfo.range.getClientRects());
        if (rect) {
          var bnd = func.rect2bnd(rect);
          showPopover($airPopover, {
            left: Math.max(bnd.left + bnd.width / 2 - PX_POPOVER_ARROW_OFFSET_X, 0),
            top: bnd.top + bnd.height
          });
        }
      } else {
        $airPopover.hide();
      }
    };

    /**
     * @param {Node} button
     * @param {String} eventName
     * @param {String} value
     */
    this.updateRecentColor = function (button, eventName, value) {
      button.updateRecentColor(button, eventName, value);
    };

    /**
     * hide all popovers
     * @param {jQuery} $popover - popover container
     */
    this.hide = function ($popover) {
      $popover.children().hide();
    };
  };

  return Popover;
});
