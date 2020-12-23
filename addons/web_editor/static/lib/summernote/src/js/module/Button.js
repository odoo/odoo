define([
  'summernote/core/list',
  'summernote/core/agent'
], function (list, agent) {
  /**
   * @class module.Button
   *
   * Button
   */
  var Button = function () {
    /**
     * update button status
     *
     * @param {jQuery} $container
     * @param {Object} styleInfo
     */
    this.update = function ($container, styleInfo) {
      /**
       * handle dropdown's check mark (for fontname, fontsize, lineHeight).
       * @param {jQuery} $btn
       * @param {Number} value
       */
      var checkDropdownMenu = function ($btn, value) {
        $btn.find('.dropdown-menu .dropdown-item').each(function () {
          // always compare string to avoid creating another func.
          var isChecked = ($(this).data('value') + '') === (value + '');
          this.className = 'dropdown-item' + (isChecked ? ' checked' : '');
        });
      };

      /**
       * update button state(active or not).
       *
       * @private
       * @param {String} selector
       * @param {Function} pred
       */
      var btnState = function (selector, pred) {
        var $btn = $container.find(selector);
        $btn.toggleClass('active', pred());
      };

      if (styleInfo.image) {
        var $img = $(styleInfo.image);

        btnState('button[data-event="imageShape"][data-value="rounded"]', function () {
          return $img.hasClass('rounded');
        });
        btnState('button[data-event="imageShape"][data-value="rounded-circle"]', function () {
          return $img.hasClass('rounded-circle');
        });
        btnState('button[data-event="imageShape"][data-value="img-thumbnail"]', function () {
          return $img.hasClass('img-thumbnail');
        });
        btnState('button[data-event="imageShape"]:not([data-value])', function () {
          return !$img.is('.rounded, .rounded-circle, .img-thumbnail');
        });

        var imgFloat = $img.css('float');
        btnState('button[data-event="floatMe"][data-value="left"]', function () {
          return imgFloat === 'left';
        });
        btnState('button[data-event="floatMe"][data-value="right"]', function () {
          return imgFloat === 'right';
        });
        btnState('button[data-event="floatMe"][data-value="none"]', function () {
          return imgFloat !== 'left' && imgFloat !== 'right';
        });

        var style = $img.attr('style');
        btnState('button[data-event="resize"][data-value="1"]', function () {
          return !!/(^|\s)(max-)?width\s*:\s*100%/.test(style);
        });
        btnState('button[data-event="resize"][data-value="0.5"]', function () {
          return !!/(^|\s)(max-)?width\s*:\s*50%/.test(style);
        });
        btnState('button[data-event="resize"][data-value="0.25"]', function () {
          return !!/(^|\s)(max-)?width\s*:\s*25%/.test(style);
        });
        return;
      }

      // fontname
      var $fontname = $container.find('.note-fontname');
      if ($fontname.length) {
        var selectedFont = styleInfo['font-family'];
        if (!!selectedFont) {

          var list = selectedFont.split(',');
          for (var i = 0, len = list.length; i < len; i++) {
            selectedFont = list[i].replace(/[\'\"]/g, '').replace(/\s+$/, '').replace(/^\s+/, '');
            if (agent.isFontInstalled(selectedFont)) {
              break;
            }
          }
          
          $fontname.find('.note-current-fontname').text(selectedFont);
          checkDropdownMenu($fontname, selectedFont);

        }
      }

      // fontsize
      var $fontsize = $container.find('.note-fontsize');
      $fontsize.find('.note-current-fontsize').text(styleInfo['font-size']);
      checkDropdownMenu($fontsize, parseFloat(styleInfo['font-size']));

      // lineheight
      var $lineHeight = $container.find('.note-height');
      checkDropdownMenu($lineHeight, parseFloat(styleInfo['line-height']));

      btnState('button[data-event="bold"]', function () {
        return styleInfo['font-bold'] === 'bold';
      });
      btnState('button[data-event="italic"]', function () {
        return styleInfo['font-italic'] === 'italic';
      });
      btnState('button[data-event="underline"]', function () {
        return styleInfo['font-underline'] === 'underline';
      });
      btnState('button[data-event="strikethrough"]', function () {
        return styleInfo['font-strikethrough'] === 'strikethrough';
      });
      btnState('button[data-event="superscript"]', function () {
        return styleInfo['font-superscript'] === 'superscript';
      });
      btnState('button[data-event="subscript"]', function () {
        return styleInfo['font-subscript'] === 'subscript';
      });
      btnState('button[data-event="justifyLeft"]', function () {
        return styleInfo['text-align'] === 'left' || styleInfo['text-align'] === 'start';
      });
      btnState('button[data-event="justifyCenter"]', function () {
        return styleInfo['text-align'] === 'center';
      });
      btnState('button[data-event="justifyRight"]', function () {
        return styleInfo['text-align'] === 'right';
      });
      btnState('button[data-event="justifyFull"]', function () {
        return styleInfo['text-align'] === 'justify';
      });
      btnState('button[data-event="insertUnorderedList"]', function () {
        return styleInfo['list-style'] === 'unordered';
      });
      btnState('button[data-event="insertOrderedList"]', function () {
        return styleInfo['list-style'] === 'ordered';
      });
    };

    /**
     * update recent color
     *
     * @param {Node} button
     * @param {String} eventName
     * @param {Mixed} value
     */
    this.updateRecentColor = function (button, eventName, value) {
      var $color = $(button).closest('.note-color');
      var $recentColor = $color.find('.note-recent-color');
      var colorInfo = JSON.parse($recentColor.attr('data-value'));
      colorInfo[eventName] = value;
      $recentColor.attr('data-value', JSON.stringify(colorInfo));
      var sKey = eventName === 'backColor' ? 'background-color' : 'color';
      $recentColor.find('i').css(sKey, value);
    };
  };

  return Button;
});
