define([
  'summernote/core/list',
  'summernote/core/dom',
  'summernote/core/key',
  'summernote/core/agent',
  'summernote/core/range'
], function (list, dom, key, agent, range) {
  var Clipboard = function (handler) {
    var $paste;

    this.attach = function (layoutInfo) {
      // [workaround] getting image from clipboard
      //  - IE11 and Firefox: CTRL+v hook
      //  - Webkit: event.clipboardData
      if (agent.isMSIE && agent.browserVersion > 10) {
        $paste = $('<div />').attr('contenteditable', true).css({
          position : 'absolute',
          left : -100000,
          opacity : 0
        });

        layoutInfo.editable().on('keydown', function (e) {
          if (e.ctrlKey && e.keyCode === key.code.V) {
            handler.invoke('saveRange', layoutInfo.editable());
            $paste.focus();

            setTimeout(function () {
              pasteByHook(layoutInfo);
            }, 0);
          }
        });

        layoutInfo.editable().before($paste);
      } else {
        layoutInfo.editable().on('paste', pasteByEvent);
      }
    };

    var pasteByHook = function (layoutInfo) {
      var $editable = layoutInfo.editable();
      var node = $paste[0].firstChild;

      if (dom.isImg(node)) {
        var dataURI = node.src;
        var decodedData = atob(dataURI.split(',')[1]);
        var array = new Uint8Array(decodedData.length);
        for (var i = 0; i < decodedData.length; i++) {
          array[i] = decodedData.charCodeAt(i);
        }

        var blob = new Blob([array], { type : 'image/png' });
        blob.name = 'clipboard.png';

        handler.invoke('restoreRange', $editable);
        handler.invoke('focus', $editable);
        handler.insertImages(layoutInfo, [blob]);
      } else {
        var pasteContent = $('<div />').html($paste.html()).html();
        handler.invoke('restoreRange', $editable);
        handler.invoke('focus', $editable);

        if (pasteContent) {
          handler.invoke('pasteHTML', $editable, pasteContent);
        }
      }

      $paste.empty();
    };

    /**
     * paste by clipboard event
     *
     * @param {Event} event
     */
    var pasteByEvent = function (event) {
      var clipboardData = event.originalEvent.clipboardData;
      var layoutInfo = dom.makeLayoutInfo(event.currentTarget || event.target);
      var $editable = layoutInfo.editable();

      if (["INPUT", "TEXTAREA"].indexOf(event.target.tagName) !== -1) {
        return;
      }

      if (clipboardData && clipboardData.items && clipboardData.items.length) {
        var item = list.head(clipboardData.items);
        if (item.kind === 'file' && item.type.indexOf('image/') !== -1) {
          handler.insertImages(layoutInfo, [item.getAsFile()]);
        }
        handler.invoke('editor.afterCommand', $editable);
      }

      event.preventDefault();

      var html = clipboardData.getData("text/html");
      var $node = $('<div/>').html(html);
      // if copying source did not provide html, default to plain text
      if(!html) {
        $node.text(clipboardData.getData("text/plain")).html(function(_, html){
          return html.replace(/\r?\n/g,'<br>');
        });
      }
      pasteContent($node, layoutInfo, $editable);
    };

    /*
        remove undesirable tag
        filter classes and style attributes
        remove undesirable attributes
    */
    var filter_tag = function ($nodes, $editable) {
      return $nodes.each(function() {
        var $node = $(this);

        if ($node.attr('style')) {
          var style = _.filter(_.compact($node.attr('style').split(/\s*;\s*/)), function (style) {
                style = style.split(/\s*:\s*/);
                return /width|height|color|background-color|font-weight|text-align|font-style|text-decoration/i.test(style[0]) &&
                   !(style[1] === 'initial' || style[1] === 'inherit' || $node.css(style[0]) === $editable.css(style[0]) ||
                    (style[0] === 'background-color' && style[1] === 'rgb(255, 255, 255)') ||
                    (style[0] === 'color' && style[1] === 'rgb(0, 0, 0)'));
              }).join(';');
          if (style.length) {
            $node.attr('style', style);
          } else {
            $node.removeAttr('style');
          }
        }

        if ($node.attr('class')) {
          var classes = _.filter($node.attr('class').split(/\s+/), function (style) {
                return /(^|\s)(fa|pull|text|bg)(\s|-|$)/.test(style);
              }).join(' ');
          if (classes.length) {
              $node.attr('class', classes);
          } else {
              $node.removeAttr('class');
          }
        }
      });
    };

    var pasteContent = function ($node, layoutInfo, $editable) {
      $node.find('meta, script, style').remove();
      filter_tag($node.find('*'), $editable).removeAttr('title', 'alt', 'id', 'contenteditable');

      /*
          remove unless span and unwant font
      */
      $node.find('span, font').filter(':not([class]):not([style])').each(function () {
        $(this).replaceWith($(this).contents());
      });
      $node.find('span + span').each(function () {
        if ($(this).attr('class') === $(this).prev().attr('class') && $(this).attr('style') === $(this).prev().attr('style')) {
          $(this).prev().append($(this).contents());
          $(this).remove();
        }
      });

      /*
          reset architecture HTML node and add <p> tag
      */
      var $arch = $('<div/>');
      var $last = $arch;
      $node.contents().each(function () {
        if (dom.isBR(this)) {
          $(this).remove();
          $last = $('<p/>');
          $arch.append($last);
        } else if (/h[0-9]+|li|table|p/i.test(this.tagName)) {
          $last = $('<p/>');
          $arch.append(this).append($last);
        } else if ($arch.is(':empty') && dom.isText(this)) {
          $last = $('<p/>').append(this);
          $arch.append($last);
        } else if (this.nodeType !== Node.COMMENT_NODE) {
          $last.append(this);
        }
      });
      $arch.find(':not([class]):not([style]):empty, p:empty').remove();

      /*
          history
      */
      $editable.data('NoteHistory').recordUndo($editable, "paste");

      /*
          remove selected content
      */
      var r = range.create();
      if (!r.isCollapsed()) {
        r = r.deleteContents();
        r.select();
      }

      /*
          insert content
      */
      var $nodes = $();
      $editable.on('DOMNodeInserted', function (event) {
        $nodes = $nodes.add(event.originalEvent.target);
      });
      window.document.execCommand('insertHTML', false,  $arch.html());
      $editable.off('DOMNodeInserted');

      /*
          clean insterted content
      */
      var $span = $nodes.filter('span');
      $span = $span.first().add($span.last());
      $span = $span.add($span.prev('span'));
      $span = $span.add($span.next('span'));
      filter_tag($span, $editable);
      $span.not('[span], [style]').each(function () {
        _.each(this.childNodes, function (node) {
          $(node.parentNode).after(node);
        });
        $(this).remove();
      });
      r = range.create();
      if (!dom.isText(r.ec)) {
        r = range.create(r.sc.childNodes[r.so], dom.nodeLength(r.sc.childNodes[r.so]));
      }
      r.clean().select();

      $editable.trigger('content_changed');
    };
  };

  return Clipboard;
});
