define([
  'summernote/core/agent',
  'summernote/core/func',
  'summernote/core/list',
  'summernote/core/dom',
  'summernote/core/range',
  'summernote/core/async',
  'summernote/editing/Style',
  'summernote/editing/Typing',
  'summernote/editing/Table',
  'summernote/editing/Bullet'
], function (agent, func, list, dom, range, async,
             Style, Typing, Table, Bullet) {

  var KEY_BOGUS = 'bogus';

  /**
   * @class editing.Editor
   *
   * Editor
   *
   */
  var Editor = function (handler) {

    var self = this;
    var style = new Style();
    var table = new Table();
    var typing = new Typing();
    var bullet = new Bullet();

    this.style = style;   // ODOO: allow access for override
    this.table = table;   // ODOO: allow access for override
    this.typing = typing; // ODOO: allow access for override
    this.bullet = bullet; // ODOO: allow access for override

    /**
     * @method createRange
     *
     * create range
     *
     * @param {jQuery} $editable
     * @return {WrappedRange}
     */
    this.createRange = function ($editable) {
      this.focus($editable);
      return range.create();
    };

    /**
     * @method saveRange
     *
     * save current range
     *
     * @param {jQuery} $editable
     * @param {Boolean} [thenCollapse=false]
     */
    this.saveRange = function ($editable, thenCollapse) {
      // ODOO: scroll to top when click on input in editable m (start_modification
      // this.focus($editable);
      var r = range.create();
      if (!r || ($editable[0] !== r.sc && !$.contains($editable[0], r.sc))) {
        $editable.focus();
      }
      // ODOO: end_modication)
      $editable.data('range', range.create());
      if (thenCollapse) {
        range.create().collapse().select();
      }
    };

    /**
     * @method saveRange
     *
     * save current node list to $editable.data('childNodes')
     *
     * @param {jQuery} $editable
     */
    this.saveNode = function ($editable) {
      // copy child node reference
      var copy = [];
      for (var key  = 0, len = $editable[0].childNodes.length; key < len; key++) {
        copy.push($editable[0].childNodes[key]);
      }
      $editable.data('childNodes', copy);
    };

    /**
     * @method restoreRange
     *
     * restore lately range
     *
     * @param {jQuery} $editable
     */
    this.restoreRange = function ($editable) {
      var rng = $editable.data('range');
      if (rng) {
        rng.select();
        this.focus($editable);
      }
    };

    /**
     * @method restoreNode
     *
     * restore lately node list
     *
     * @param {jQuery} $editable
     */
    this.restoreNode = function ($editable) {
      $editable.html('');
      var child = $editable.data('childNodes');
      for (var index = 0, len = child.length; index < len; index++) {
        $editable[0].appendChild(child[index]);
      }
    };

    /**
     * @method currentStyle
     *
     * current style
     *
     * @param {Node} target
     * @return {Object|Boolean} unfocus
     */
    this.currentStyle = function (target) {
      var rng = range.create();
      var styleInfo =  rng && rng.isOnEditable() ? style.current(rng.normalize()) : {};
      if (dom.isImg(target)) {
        styleInfo.image = target;
      }
      return styleInfo;
    };

    /**
     * style from node
     *
     * @param {jQuery} $node
     * @return {Object}
     */
    this.styleFromNode = function ($node) {
      return style.fromNode($node);
    };

    var triggerOnBeforeChange = function ($editable) {
      var $holder = dom.makeLayoutInfo($editable).holder();
      handler.bindCustomEvent(
        $holder, $editable.data('callbacks'), 'before.command'
      )($editable.html(), $editable);
    };

    var triggerOnChange = function ($editable) {
      var $holder = dom.makeLayoutInfo($editable).holder();
      handler.bindCustomEvent(
        $holder, $editable.data('callbacks'), 'change'
      )($editable.html(), $editable);
    };

    /**
     * @method undo
     * undo
     * @param {jQuery} $editable
     */
    this.undo = function ($editable) {
      triggerOnBeforeChange($editable);
      $editable.data('NoteHistory').undo();
      triggerOnChange($editable);
    };

    /**
     * @method redo
     * redo
     * @param {jQuery} $editable
     */
    this.redo = function ($editable) {
      triggerOnBeforeChange($editable);
      $editable.data('NoteHistory').redo();
      triggerOnChange($editable);
    };

    /**
     * @method beforeCommand
     * before command
     * @param {jQuery} $editable
     */
    var beforeCommand = this.beforeCommand = function ($editable) {
      triggerOnBeforeChange($editable);
      // keep focus on editable before command execution
      self.focus($editable);
    };

    /**
     * @method afterCommand
     * after command
     * @param {jQuery} $editable
     * @param {Boolean} isPreventTrigger
     */
    var afterCommand = this.afterCommand = function ($editable, isPreventTrigger) {
      $editable.data('NoteHistory').recordUndo();
      if (!isPreventTrigger) {
        triggerOnChange($editable);
      }
    };

    /**
     * @method bold
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method italic
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method underline
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method strikethrough
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method formatBlock
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method superscript
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method subscript
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method justifyLeft
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method justifyCenter
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method justifyRight
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method justifyFull
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method formatBlock
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method removeFormat
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method backColor
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method foreColor
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method insertHorizontalRule
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /**
     * @method fontName
     *
     * change font name
     *
     * @param {jQuery} $editable
     * @param {Mixed} value
     */

    /* jshint ignore:start */
    // native commands(with execCommand), generate function for execCommand
    var commands = ['bold', 'italic', 'underline', 'strikethrough', 'superscript', 'subscript',
                    'justifyLeft', 'justifyCenter', 'justifyRight', 'justifyFull',
                    'formatBlock', 'removeFormat',
                    'backColor', 'foreColor', 'fontName'];

    for (var idx = 0, len = commands.length; idx < len; idx ++) {
      this[commands[idx]] = (function (sCmd) {
        return function ($editable, value) {
          beforeCommand($editable);

          document.execCommand(sCmd, false, value);

          afterCommand($editable, true);
        };
      })(commands[idx]);
    }
    /* jshint ignore:end */

    /**
     * @method tab
     *
     * handle tab key
     *
     * @param {jQuery} $editable
     * @param {Object} options
     */
    this.tab = function ($editable, options) {
      var rng = this.createRange($editable);
      if (rng.isCollapsed() && rng.isOnCell()) {
        table.tab(rng);
      } else {
        beforeCommand($editable);
        typing.insertTab($editable, rng, options.tabsize);
        afterCommand($editable);
      }
    };

    /**
     * @method untab
     *
     * handle shift+tab key
     *
     */
    this.untab = function ($editable) {
      var rng = this.createRange($editable);
      if (rng.isCollapsed() && rng.isOnCell()) {
        table.tab(rng, true);
      }
    };

    /**
     * @method insertParagraph
     *
     * insert paragraph
     *
     * @param {Node} $editable
     */
    this.insertParagraph = function ($editable) {
      beforeCommand($editable);
      typing.insertParagraph($editable);
      afterCommand($editable);
    };

    /**
     * @method insertOrderedList
     *
     * @param {jQuery} $editable
     */
    this.insertOrderedList = function ($editable) {
      beforeCommand($editable);
      bullet.insertOrderedList($editable);
      afterCommand($editable);
    };

    /**
     * @param {jQuery} $editable
     */
    this.insertUnorderedList = function ($editable) {
      beforeCommand($editable);
      bullet.insertUnorderedList($editable);
      afterCommand($editable);
    };

    /**
     * @param {jQuery} $editable
     */
    this.indent = function ($editable) {
      beforeCommand($editable);
      bullet.indent($editable);
      afterCommand($editable);
    };

    /**
     * @param {jQuery} $editable
     */
    this.outdent = function ($editable) {
      beforeCommand($editable);
      bullet.outdent($editable);
      afterCommand($editable);
    };

    /**
     * insert image
     *
     * @param {jQuery} $editable
     * @param {String} sUrl
     */
    this.insertImage = function ($editable, sUrl, filename) {
      async.createImage(sUrl, filename).then(function ($image) {
        beforeCommand($editable);
        $image.css({
          display: '',
          width: Math.min($editable.width(), $image.width())
        });
        range.create().insertNode($image[0]);
        range.createFromNodeAfter($image[0]).select();
        afterCommand($editable);
      }).fail(function () {
        var $holder = dom.makeLayoutInfo($editable).holder();
        handler.bindCustomEvent(
          $holder, $editable.data('callbacks'), 'image.upload.error'
        )();
      });
    };

    /**
     * @method insertNode
     * insert node
     * @param {Node} $editable
     * @param {Node} node
     */
    this.insertNode = function ($editable, node) {
      beforeCommand($editable);
      range.create().insertNode(node);
      range.createFromNodeAfter(node).select();
      afterCommand($editable);
    };

    /**
     * insert text
     * @param {Node} $editable
     * @param {String} text
     */
    this.insertText = function ($editable, text) {
      beforeCommand($editable);
      var textNode = range.create().insertNode(dom.createText(text));
      range.create(textNode, dom.nodeLength(textNode)).select();
      afterCommand($editable);
    };

    /**
     * paste HTML
     * @param {Node} $editable
     * @param {String} markup
     */
    this.pasteHTML = function ($editable, markup) {
      beforeCommand($editable);
      var contents = range.create().pasteHTML(markup);
      range.createFromNodeAfter(list.last(contents)).select();
      afterCommand($editable);
    };

    /**
     * formatBlock
     *
     * @param {jQuery} $editable
     * @param {String} tagName
     */
    this.formatBlock = function ($editable, tagName) {
      beforeCommand($editable);
      // [workaround] for MSIE, IE need `<`
      tagName = agent.isMSIE ? '<' + tagName + '>' : tagName;
      document.execCommand('FormatBlock', false, tagName);
      afterCommand($editable);
    };

    this.formatPara = function ($editable) {
      beforeCommand($editable);
      this.formatBlock($editable, 'P');
      afterCommand($editable);
    };

    /* jshint ignore:start */
    for (var idx = 1; idx <= 6; idx ++) {
      this['formatH' + idx] = function (idx) {
        return function ($editable) {
          this.formatBlock($editable, 'H' + idx);
        };
      }(idx);
    };
    /* jshint ignore:end */

    /**
     * fontSize
     *
     * @param {jQuery} $editable
     * @param {String} value - px
     */
    this.fontSize = function ($editable, value) {
      var rng = range.create();

      if (rng.isCollapsed()) {
        var spans = style.styleNodes(rng);
        var firstSpan = list.head(spans);

        $(spans).css({
          'font-size': value + 'px'
        });

        // [workaround] added styled bogus span for style
        //  - also bogus character needed for cursor position
        if (firstSpan && !dom.nodeLength(firstSpan)) {
          firstSpan.innerHTML = dom.ZERO_WIDTH_NBSP_CHAR;
          range.createFromNodeAfter(firstSpan.firstChild).select();
          $editable.data(KEY_BOGUS, firstSpan);
        }
      } else {
        beforeCommand($editable);
        $(style.styleNodes(rng)).css({
          'font-size': value + 'px'
        });
        afterCommand($editable);
      }
    };

    /**
     * insert horizontal rule
     * @param {jQuery} $editable
     */
    this.insertHorizontalRule = function ($editable) {
      beforeCommand($editable);

      var rng = range.create();
      var hrNode = rng.insertNode($('<HR/>')[0]);
      if (hrNode.nextSibling) {
        range.create(hrNode.nextSibling, 0).normalize().select();
      }

      afterCommand($editable);
    };

    /**
     * remove bogus node and character
     */
    this.removeBogus = function ($editable) {
      var bogusNode = $editable.data(KEY_BOGUS);
      if (!bogusNode) {
        return;
      }

      var textNode = list.find(list.from(bogusNode.childNodes), dom.isText);

      var bogusCharIdx = textNode.nodeValue.indexOf(dom.ZERO_WIDTH_NBSP_CHAR);
      if (bogusCharIdx !== -1) {
        textNode.deleteData(bogusCharIdx, 1);
      }

      if (dom.isEmpty(bogusNode)) {
        dom.remove(bogusNode);
      }

      $editable.removeData(KEY_BOGUS);
    };

    /**
     * lineHeight
     * @param {jQuery} $editable
     * @param {String} value
     */
    this.lineHeight = function ($editable, value) {
      beforeCommand($editable);
      style.stylePara(range.create(), {
        lineHeight: value
      });
      afterCommand($editable);
    };

    /**
     * unlink
     *
     * @type command
     *
     * @param {jQuery} $editable
     */
    this.unlink = function ($editable) {
      var rng = this.createRange($editable);
      if (rng.isOnAnchor()) {
        var anchor = dom.ancestor(rng.sc, dom.isAnchor);
        rng = range.createFromNode(anchor);
        rng.select();

        beforeCommand($editable);
        document.execCommand('unlink');
        afterCommand($editable);
      }
    };

    /**
     * create link (command)
     *
     * @param {jQuery} $editable
     * @param {Object} linkInfo
     * @param {Object} options
     */
    this.createLink = function ($editable, linkInfo, options) {
      var linkUrl = linkInfo.url;
      var linkText = linkInfo.text;
      var isNewWindow = linkInfo.isNewWindow;
      var className = linkInfo.className || null; // ODOO: addition
      var rng = linkInfo.range || this.createRange($editable);
      var isTextChanged = rng.toString() !== linkText;

      options = options || dom.makeLayoutInfo($editable).editor().data('options');

      beforeCommand($editable);

      if (options.onCreateLink) {
        linkUrl = options.onCreateLink(linkUrl);
      }

      var anchors = [];
      // ODOO: adding this branch to modify existing anchor
      var ancestor_anchor = dom.ancestor(rng.sc, dom.isAnchor);
      if(ancestor_anchor) {
          anchors.push($(ancestor_anchor).html(linkText).get(0));
      } else if (isTextChanged) {
        // Create a new link when text changed.
        var anchor = rng.insertNode($('<A>' + linkText + '</A>')[0]);
        anchors.push(anchor);
      } else {
        anchors = style.styleNodes(rng, {
          nodeName: 'A',
          expandClosestSibling: true,
          onlyPartialContains: true
        });
      }

      $.each(anchors, function (idx, anchor) {
        $(anchor).attr('href', linkUrl);
        $(anchor).attr('class', className); // ODOO: addition
        if (isNewWindow) {
          $(anchor).attr('target', '_blank');
        } else {
          $(anchor).removeAttr('target');
        }
      });

      var startRange = range.createFromNodeBefore(list.head(anchors));
      var startPoint = startRange.getStartPoint();
      var endRange = range.createFromNodeAfter(list.last(anchors));
      var endPoint = endRange.getEndPoint();

      range.create(
        startPoint.node,
        startPoint.offset,
        endPoint.node,
        endPoint.offset
      ).select();

      afterCommand($editable);
    };

    /**
     * returns link info
     *
     * @return {Object}
     * @return {WrappedRange} return.range
     * @return {String} return.text
     * @return {Boolean} [return.isNewWindow=true]
     * @return {String} [return.url=""]
     */
    this.getLinkInfo = function ($editable) {
      this.focus($editable);

      var rng = range.create().expand(dom.isAnchor);

      // Get the first anchor on range(for edit).
      var $anchor = $(list.head(rng.nodes(dom.isAnchor)));

      return {
        range: rng,
        text: rng.toString(),
        isNewWindow: $anchor.length ? $anchor.attr('target') === '_blank' : false,
        url: $anchor.length ? $anchor.attr('href') : ''
      };
    };

    /**
     * setting color
     *
     * @param {Node} $editable
     * @param {Object} sObjColor  color code
     * @param {String} sObjColor.foreColor foreground color
     * @param {String} sObjColor.backColor background color
     */
    this.color = function ($editable, sObjColor) {
      var oColor = JSON.parse(sObjColor);
      var foreColor = oColor.foreColor, backColor = oColor.backColor;

      beforeCommand($editable);

      if (foreColor) { document.execCommand('foreColor', false, foreColor); }
      if (backColor) { document.execCommand('backColor', false, backColor); }

      afterCommand($editable);
    };

    /**
     * insert Table
     *
     * @param {Node} $editable
     * @param {String} sDim dimension of table (ex : "5x5")
     */
    this.insertTable = function ($editable, sDim) {
      var dimension = sDim.split('x');
      beforeCommand($editable);

      var rng = range.create().deleteContents();
      rng.insertNode(table.createTable(dimension[0], dimension[1]));
      afterCommand($editable);
    };

    /**
     * float me
     *
     * @param {jQuery} $editable
     * @param {String} value
     * @param {jQuery} $target
     */
    this.floatMe = function ($editable, value, $target) {
      beforeCommand($editable);
      // bootstrap
      $target.removeClass('pull-left pull-right');
      if (value && value !== 'none') {
        $target.addClass('pull-' + value);
      }

      // fallback for non-bootstrap
      $target.css('float', value);
      afterCommand($editable);
    };

    /**
     * change image shape
     *
     * @param {jQuery} $editable
     * @param {String} value css class
     * @param {Node} $target
     */
    this.imageShape = function ($editable, value, $target) {
      beforeCommand($editable);

      $target.removeClass('img-rounded img-circle img-thumbnail');

      if (value) {
        $target.addClass(value);
      }

      afterCommand($editable);
    };

    /**
     * resize overlay element
     * @param {jQuery} $editable
     * @param {String} value
     * @param {jQuery} $target - target element
     */
    this.resize = function ($editable, value, $target) {
      beforeCommand($editable);

      $target.css({
        width: value * 100 + '%',
        height: ''
      });

      afterCommand($editable);
    };

    /**
     * @param {Position} pos
     * @param {jQuery} $target - target element
     * @param {Boolean} [bKeepRatio] - keep ratio
     */
    this.resizeTo = function (pos, $target, bKeepRatio) {
      var imageSize;
      if (bKeepRatio) {
        var newRatio = pos.y / pos.x;
        var ratio = $target.data('ratio');
        imageSize = {
          width: ratio > newRatio ? pos.x : pos.y / ratio,
          height: ratio > newRatio ? pos.x * ratio : pos.y
        };
      } else {
        imageSize = {
          width: pos.x,
          height: pos.y
        };
      }

      $target.css(imageSize);
    };

    /**
     * remove media object
     *
     * @param {jQuery} $editable
     * @param {String} value - dummy argument (for keep interface)
     * @param {jQuery} $target - target element
     */
    this.removeMedia = function ($editable, value, $target) {
      beforeCommand($editable);
      $target.detach();

      handler.bindCustomEvent(
        $(), $editable.data('callbacks'), 'media.delete'
      )($target, $editable);

      afterCommand($editable);
    };

    /**
     * set focus
     *
     * @param $editable
     */
    this.focus = function ($editable) {
      $editable.focus();

      // [workaround] for firefox bug http://goo.gl/lVfAaI
      if (agent.isFF) {
        var rng = range.create();
        if (!rng || rng.isOnEditable()) {
          return;
        }

        range.createFromNode($editable[0])
             .normalize()
             .collapse()
             .select();
      }
    };

    /**
     * returns whether contents is empty or not.
     *
     * @param {jQuery} $editable
     * @return {Boolean}
     */
    this.isEmpty = function ($editable) {
      return dom.isEmpty($editable[0]) || dom.emptyPara === $editable.html();
    };
  };

  return Editor;
});
