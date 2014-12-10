define([
  'summernote/core/agent', 'summernote/core/dom', 'summernote/core/async', 'summernote/core/key', 'summernote/core/list',
  'summernote/editing/Style', 'summernote/editing/Editor', 'summernote/editing/History',
  'summernote/module/Toolbar', 'summernote/module/Popover', 'summernote/module/Handle', 'summernote/module/Dialog'
], function (agent, dom, async, key, list,
             Style, Editor, History,
             Toolbar, Popover, Handle, Dialog) {

  var CodeMirror;
  if (agent.hasCodeMirror) {
    if (agent.isSupportAmd) {
      require(['CodeMirror'], function (cm) {
        CodeMirror = cm;
      });
    } else {
      CodeMirror = window.CodeMirror;
    }
  }

  /**
   * EventHandler
   */
  var EventHandler = function () {
    var $window = $(window);
    var $document = $(document);
    var $scrollbar = $('html, body');

    var editor = new Editor();
    var toolbar = new Toolbar(), popover = new Popover();
    var handle = new Handle(), dialog = new Dialog();

    this.getEditor = function () {
      return editor;
    };

    /**
     * returns makeLayoutInfo from editor's descendant node.
     *
     * @param {Node} descendant
     * @returns {Object}
     */
    var makeLayoutInfo = function (descendant) {
      var $target = $(descendant).closest('.note-editor, .note-air-editor, .note-air-layout');

      if (!$target.length) { return null; }

      var $editor;
      if ($target.is('.note-editor, .note-air-editor')) {
        $editor = $target;
      } else {
        $editor = $('#note-editor-' + list.last($target.attr('id').split('-')));
      }

      return dom.buildLayoutInfo($editor);
    };

    /**
     * insert Images from file array.
     *
     * @param {Object} layoutInfo
     * @param {File[]} files
     */
    var insertImages = function (layoutInfo, files) {
      var $editor = layoutInfo.editor(),
          $editable = layoutInfo.editable();

      var callbacks = $editable.data('callbacks');
      var options = $editor.data('options');

      // If onImageUpload options setted
      if (callbacks.onImageUpload) {
        callbacks.onImageUpload(files, editor, $editable);
      // else insert Image as dataURL
      } else {
        $.each(files, function (idx, file) {
          var filename = file.name;
          if (options.maximumImageFileSize && options.maximumImageFileSize < file.size) {
            if (callbacks.onImageUploadError) {
              callbacks.onImageUploadError(options.langInfo.image.maximumFileSizeError);
            } else {
              alert(options.langInfo.image.maximumFileSizeError);
            }
          } else {
            async.readFileAsDataURL(file).then(function (sDataURL) {
              editor.insertImage($editable, sDataURL, filename);
            }).fail(function () {
              if (callbacks.onImageUploadError) {
                callbacks.onImageUploadError();
              }
            });
          }
        });
      }
    };

    var commands = {
      /**
       * @param {Object} layoutInfo
       */
      showLinkDialog: function (layoutInfo) {
        var $editor = layoutInfo.editor(),
            $dialog = layoutInfo.dialog(),
            $editable = layoutInfo.editable(),
            linkInfo = editor.getLinkInfo($editable);

        var options = $editor.data('options');

        editor.saveRange($editable);
        dialog.showLinkDialog($editable, $dialog, linkInfo).then(function (linkInfo) {
          editor.restoreRange($editable);
          editor.createLink($editable, linkInfo, options);
          // hide popover after creating link
          popover.hide(layoutInfo.popover());
        }).fail(function () {
          editor.restoreRange($editable);
        });
      },

      /**
       * @param {Object} layoutInfo
       */
      showImageDialog: function (layoutInfo) {
        var $dialog = layoutInfo.dialog(),
            $editable = layoutInfo.editable();

        editor.saveRange($editable);
        dialog.showImageDialog($editable, $dialog).then(function (data) {
          editor.restoreRange($editable);

          if (typeof data === 'string') {
            // image url
            editor.insertImage($editable, data);
          } else {
            // array of files
            insertImages(layoutInfo, data);
          }
        }).fail(function () {
          editor.restoreRange($editable);
        });
      },

      /**
       * @param {Object} layoutInfo
       */
      showHelpDialog: function (layoutInfo) {
        var $dialog = layoutInfo.dialog(),
            $editable = layoutInfo.editable();

        editor.saveRange($editable, true);
        dialog.showHelpDialog($editable, $dialog).then(function () {
          editor.restoreRange($editable);
        });
      },

      fullscreen: function (layoutInfo) {
        var $editor = layoutInfo.editor(),
        $toolbar = layoutInfo.toolbar(),
        $editable = layoutInfo.editable(),
        $codable = layoutInfo.codable();

        var resize = function (size) {
          $editable.css('height', size.h);
          $codable.css('height', size.h);
          if ($codable.data('cmeditor')) {
            $codable.data('cmeditor').setsize(null, size.h);
          }
        };

        $editor.toggleClass('fullscreen');
        var isFullscreen = $editor.hasClass('fullscreen');
        if (isFullscreen) {
          $editable.data('orgheight', $editable.css('height'));

          $window.on('resize', function () {
            resize({
              h: $window.height() - $toolbar.outerHeight()
            });
          }).trigger('resize');

          $scrollbar.css('overflow', 'hidden');
        } else {
          $window.off('resize');
          resize({
            h: $editable.data('orgheight')
          });
          $scrollbar.css('overflow', 'visible');
        }

        toolbar.updateFullscreen($toolbar, isFullscreen);
      },

      codeview: function (layoutInfo) {
        var $editor = layoutInfo.editor(),
        $toolbar = layoutInfo.toolbar(),
        $editable = layoutInfo.editable(),
        $codable = layoutInfo.codable(),
        $popover = layoutInfo.popover(),
        $handle = layoutInfo.handle();

        var options = $editor.data('options');

        var cmEditor, server;

        $editor.toggleClass('codeview');

        var isCodeview = $editor.hasClass('codeview');
        if (isCodeview) {
          $codable.val(dom.html($editable, true));
          $codable.height($editable.height());
          toolbar.deactivate($toolbar);
          popover.hide($popover);
          handle.hide($handle);
          $codable.focus();

          // activate CodeMirror as codable
          if (agent.hasCodeMirror) {
            cmEditor = CodeMirror.fromTextArea($codable[0], options.codemirror);

            // CodeMirror TernServer
            if (options.codemirror.tern) {
              server = new CodeMirror.TernServer(options.codemirror.tern);
              cmEditor.ternServer = server;
              cmEditor.on('cursorActivity', function (cm) {
                server.updateArgHints(cm);
              });
            }

            // CodeMirror hasn't Padding.
            cmEditor.setSize(null, $editable.outerHeight());
            $codable.data('cmEditor', cmEditor);
          }
        } else {
          // deactivate CodeMirror as codable
          if (agent.hasCodeMirror) {
            cmEditor = $codable.data('cmEditor');
            $codable.val(cmEditor.getValue());
            cmEditor.toTextArea();
          }

          $editable.html(dom.value($codable) || dom.emptyPara);
          $editable.height(options.height ? $codable.height() : 'auto');

          toolbar.activate($toolbar);
          $editable.focus();
        }

        toolbar.updateCodeview(layoutInfo.toolbar(), isCodeview);
      }
    };

    var hMousedown = function (event) {
      //preventDefault Selection for FF, IE8+
      if (dom.isImg(event.target)) {
        event.preventDefault();
      }
    };

    var hToolbarAndPopoverUpdate = function (event) {
      // delay for range after mouseup
      setTimeout(function () {
        var layoutInfo = makeLayoutInfo(event.currentTarget || event.target);
        var styleInfo = editor.currentStyle(event.target);
        if (!styleInfo) { return; }

        var isAirMode = layoutInfo.editor().data('options').airMode;
        if (!isAirMode) {
          toolbar.update(layoutInfo.toolbar(), styleInfo);
        }

        popover.update(layoutInfo.popover(), styleInfo, isAirMode);
        handle.update(layoutInfo.handle(), styleInfo, isAirMode);
      }, 0);
    };

    var hScroll = function (event) {
      var layoutInfo = makeLayoutInfo(event.currentTarget || event.target);
      //hide popover and handle when scrolled
      popover.hide(layoutInfo.popover());
      handle.hide(layoutInfo.handle());
    };

    /**
     * paste clipboard image
     *
     * @param {Event} event
     */
    var hPasteClipboardImage = function (event) {
      var clipboardData = event.originalEvent.clipboardData;
      if (!clipboardData || !clipboardData.items || !clipboardData.items.length) {
        return;
      }

      var layoutInfo = makeLayoutInfo(event.currentTarget || event.target),
          $editable = layoutInfo.editable();

      var item = list.head(clipboardData.items);
      var isClipboardImage = item.kind === 'file' && item.type.indexOf('image/') !== -1;

      if (isClipboardImage) {
        insertImages(layoutInfo, [item.getAsFile()]);
      }

      editor.afterCommand($editable);
    };

    /**
     * `mousedown` event handler on $handle
     *  - controlSizing: resize image
     *
     * @param {MouseEvent} event
     */
    var hHandleMousedown = function (event) {
      if (dom.isControlSizing(event.target)) {
        event.preventDefault();
        event.stopPropagation();

        var layoutInfo = makeLayoutInfo(event.target),
            $handle = layoutInfo.handle(), $popover = layoutInfo.popover(),
            $editable = layoutInfo.editable(),
            $editor = layoutInfo.editor();

        var target = $handle.find('.note-control-selection').data('target'),
            $target = $(target), posStart = $target.offset(),
            scrollTop = $document.scrollTop();

        var isAirMode = $editor.data('options').airMode;

        $document.on('mousemove', function (event) {
          editor.resizeTo({
            x: event.clientX - posStart.left,
            y: event.clientY - (posStart.top - scrollTop)
          }, $target, !event.shiftKey);

          handle.update($handle, {image: target}, isAirMode);
          popover.update($popover, {image: target}, isAirMode);
        }).one('mouseup', function () {
          $document.off('mousemove');
          editor.afterCommand($editable);
        });

        if (!$target.data('ratio')) { // original ratio.
          $target.data('ratio', $target.height() / $target.width());
        }
      }
    };

    var hToolbarAndPopoverMousedown = function (event) {
      // prevent default event when insertTable (FF, Webkit)
      var $btn = $(event.target).closest('[data-event]');
      if ($btn.length) {
        event.preventDefault();
      }
    };

    var hToolbarAndPopoverClick = function (event) {
      var $btn = $(event.target).closest('[data-event]');

      if ($btn.length) {
        var eventName = $btn.attr('data-event'),
            value = $btn.attr('data-value'),
            hide = $btn.attr('data-hide');

        var layoutInfo = makeLayoutInfo(event.target);

        event.preventDefault();

        // before command: detect control selection element($target)
        var $target;
        if ($.inArray(eventName, ['resize', 'floatMe', 'removeMedia', 'imageShape']) !== -1) {
          var $selection = layoutInfo.handle().find('.note-control-selection');
          $target = $($selection.data('target'));
        }

        // If requested, hide the popover when the button is clicked.
        // Useful for things like showHelpDialog.
        if (hide) {
          $btn.parents('.popover').hide();
        }

        if (editor[eventName]) { // on command
          var $editable = layoutInfo.editable();
          $editable.trigger('focus');
          editor[eventName]($editable, value, $target);
        } else if (commands[eventName]) {
          commands[eventName].call(this, layoutInfo);
        } else if ($.isFunction($.summernote.pluginEvents[eventName])) {
          $.summernote.pluginEvents[eventName](layoutInfo, value, $target);
        }

        // after command
        if ($.inArray(eventName, ['backColor', 'foreColor']) !== -1) {
          var options = layoutInfo.editor().data('options', options);
          var module = options.airMode ? popover : toolbar;
          module.updateRecentColor(list.head($btn), eventName, value);
        }

        hToolbarAndPopoverUpdate(event);
      }
    };

    var EDITABLE_PADDING = 24;
    /**
     * `mousedown` event handler on statusbar
     *
     * @param {MouseEvent} event
     */
    var hStatusbarMousedown = function (event) {
      event.preventDefault();
      event.stopPropagation();

      var $editable = makeLayoutInfo(event.target).editable();
      var nEditableTop = $editable.offset().top - $document.scrollTop();

      var layoutInfo = makeLayoutInfo(event.currentTarget || event.target);
      var options = layoutInfo.editor().data('options');

      $document.on('mousemove', function (event) {
        var nHeight = event.clientY - (nEditableTop + EDITABLE_PADDING);

        nHeight = (options.minHeight > 0) ? Math.max(nHeight, options.minHeight) : nHeight;
        nHeight = (options.maxHeight > 0) ? Math.min(nHeight, options.maxHeight) : nHeight;

        $editable.height(nHeight);
      }).one('mouseup', function () {
        $document.off('mousemove');
      });
    };

    var PX_PER_EM = 18;
    var hDimensionPickerMove = function (event, options) {
      var $picker = $(event.target.parentNode); // target is mousecatcher
      var $dimensionDisplay = $picker.next();
      var $catcher = $picker.find('.note-dimension-picker-mousecatcher');
      var $highlighted = $picker.find('.note-dimension-picker-highlighted');
      var $unhighlighted = $picker.find('.note-dimension-picker-unhighlighted');

      var posOffset;
      // HTML5 with jQuery - e.offsetX is undefined in Firefox
      if (event.offsetX === undefined) {
        var posCatcher = $(event.target).offset();
        posOffset = {
          x: event.pageX - posCatcher.left,
          y: event.pageY - posCatcher.top
        };
      } else {
        posOffset = {
          x: event.offsetX,
          y: event.offsetY
        };
      }

      var dim = {
        c: Math.ceil(posOffset.x / PX_PER_EM) || 1,
        r: Math.ceil(posOffset.y / PX_PER_EM) || 1
      };

      $highlighted.css({ width: dim.c + 'em', height: dim.r + 'em' });
      $catcher.attr('data-value', dim.c + 'x' + dim.r);

      if (3 < dim.c && dim.c < options.insertTableMaxSize.col) {
        $unhighlighted.css({ width: dim.c + 1 + 'em'});
      }

      if (3 < dim.r && dim.r < options.insertTableMaxSize.row) {
        $unhighlighted.css({ height: dim.r + 1 + 'em'});
      }

      $dimensionDisplay.html(dim.c + ' x ' + dim.r);
    };

    /**
     * Drag and Drop Events
     *
     * @param {Object} layoutInfo - layout Informations
     * @param {Object} options
     */
    var handleDragAndDropEvent = function (layoutInfo, options) {
      if (options.disableDragAndDrop) {
        // prevent default drop event
        $document.on('drop', function (e) {
          e.preventDefault();
        });
      } else {
        attachDragAndDropEvent(layoutInfo, options);
      }
    };

    /**
     * attach Drag and Drop Events
     *
     * @param {Object} layoutInfo - layout Informations
     * @param {Object} options
     */
    var attachDragAndDropEvent = function (layoutInfo, options) {
      var collection = $(),
          $dropzone = layoutInfo.dropzone,
          $dropzoneMessage = layoutInfo.dropzone.find('.note-dropzone-message');

      // show dropzone on dragenter when dragging a object to document.
      $document.on('dragenter', function (e) {
        var isCodeview = layoutInfo.editor.hasClass('codeview');
        if (!isCodeview && !collection.length) {
          layoutInfo.editor.addClass('dragover');
          $dropzone.width(layoutInfo.editor.width());
          $dropzone.height(layoutInfo.editor.height());
          $dropzoneMessage.text(options.langInfo.image.dragImageHere);
        }
        collection = collection.add(e.target);
      }).on('dragleave', function (e) {
        collection = collection.not(e.target);
        if (!collection.length) {
          layoutInfo.editor.removeClass('dragover');
        }
      }).on('drop', function () {
        collection = $();
        layoutInfo.editor.removeClass('dragover');
      });

      // change dropzone's message on hover.
      $dropzone.on('dragenter', function () {
        $dropzone.addClass('hover');
        $dropzoneMessage.text(options.langInfo.image.dropImage);
      }).on('dragleave', function () {
        $dropzone.removeClass('hover');
        $dropzoneMessage.text(options.langInfo.image.dragImageHere);
      });

      // attach dropImage
      $dropzone.on('drop', function (event) {
        event.preventDefault();

        var dataTransfer = event.originalEvent.dataTransfer;
        if (dataTransfer && dataTransfer.files) {
          var layoutInfo = makeLayoutInfo(event.currentTarget || event.target);
          layoutInfo.editable().focus();
          insertImages(layoutInfo, dataTransfer.files);
        }
      }).on('dragover', false); // prevent default dragover event
    };


    /**
     * bind KeyMap on keydown
     *
     * @param {Object} layoutInfo
     * @param {Object} keyMap
     */
    this.bindKeyMap = function (layoutInfo, keyMap) {
      var $editor = layoutInfo.editor;
      var $editable = layoutInfo.editable;

      layoutInfo = makeLayoutInfo($editable);

      $editable.on('keydown', function (event) {
        var aKey = [];

        // modifier
        if (event.metaKey) { aKey.push('CMD'); }
        if (event.ctrlKey && !event.altKey) { aKey.push('CTRL'); }
        if (event.shiftKey) { aKey.push('SHIFT'); }

        // keycode
        var keyName = key.nameFromCode[event.keyCode];
        if (keyName) { aKey.push(keyName); }

        var eventName = keyMap[aKey.join('+')];
        if (eventName) {
          event.preventDefault();

          if (editor[eventName]) {
            editor[eventName]($editable, $editor.data('options'));
          } else if (commands[eventName]) {
            commands[eventName].call(this, layoutInfo);
          } else if ($.summernote.plugins[eventName]) {
            var plugin = $.summernote.plugins[eventName];
            if ($.isFunction(plugin.event)) {
              plugin.event(event, editor, layoutInfo);
            }
          }
        } else if (key.isEdit(event.keyCode)) {
          editor.afterCommand($editable);
        }
      });
    };

    /**
     * attach eventhandler
     *
     * @param {Object} layoutInfo - layout Informations
     * @param {Object} options - user options include custom event handlers
     * @param {Function} options.enter - enter key handler
     */
    this.attach = function (layoutInfo, options) {
      // handlers for editable
      if (options.shortcuts) {
        this.bindKeyMap(layoutInfo, options.keyMap[agent.isMac ? 'mac' : 'pc']);
      }
      layoutInfo.editable.on('mousedown', hMousedown);
      layoutInfo.editable.on('keyup mouseup', hToolbarAndPopoverUpdate);
      layoutInfo.editable.on('scroll', hScroll);
      layoutInfo.editable.on('paste', hPasteClipboardImage);

      // handler for handle and popover
      layoutInfo.handle.on('mousedown', hHandleMousedown);
      layoutInfo.popover.on('click', hToolbarAndPopoverClick);
      layoutInfo.popover.on('mousedown', hToolbarAndPopoverMousedown);

      // handlers for frame mode (toolbar, statusbar)
      if (!options.airMode) {
        // handler for drag and drop
        handleDragAndDropEvent(layoutInfo, options);

        // handler for toolbar
        layoutInfo.toolbar.on('click', hToolbarAndPopoverClick);
        layoutInfo.toolbar.on('mousedown', hToolbarAndPopoverMousedown);

        // handler for statusbar
        if (!options.disableResizeEditor) {
          layoutInfo.statusbar.on('mousedown', hStatusbarMousedown);
        }
      }

      // handler for table dimension
      var $catcherContainer = options.airMode ? layoutInfo.popover :
                                                layoutInfo.toolbar;
      var $catcher = $catcherContainer.find('.note-dimension-picker-mousecatcher');
      $catcher.css({
        width: options.insertTableMaxSize.col + 'em',
        height: options.insertTableMaxSize.row + 'em'
      }).on('mousemove', function (event) {
        hDimensionPickerMove(event, options);
      });

      // save options on editor
      layoutInfo.editor.data('options', options);

      // ret styleWithCSS for backColor / foreColor clearing with 'inherit'.
      if (!agent.isMSIE) {
        // protect FF Error: NS_ERROR_FAILURE: Failure
        setTimeout(function () {
          document.execCommand('styleWithCSS', 0, options.styleWithSpan);
        }, 0);
      }

      // History
      var history = new History(layoutInfo.editable);
      layoutInfo.editable.data('NoteHistory', history);

      // basic event callbacks (lowercase)
      // enter, focus, blur, keyup, keydown
      if (options.onenter) {
        layoutInfo.editable.keypress(function (event) {
          if (event.keyCode === key.ENTER) { options.onenter(event); }
        });
      }

      if (options.onfocus) { layoutInfo.editable.focus(options.onfocus); }
      if (options.onblur) { layoutInfo.editable.blur(options.onblur); }
      if (options.onkeyup) { layoutInfo.editable.keyup(options.onkeyup); }
      if (options.onkeydown) { layoutInfo.editable.keydown(options.onkeydown); }
      if (options.onpaste) { layoutInfo.editable.on('paste', options.onpaste); }

      // callbacks for advanced features (camel)
      if (options.onToolbarClick) { layoutInfo.toolbar.click(options.onToolbarClick); }
      if (options.onChange) {
        var hChange = function () {
          editor.triggerOnChange(layoutInfo.editable);
        };

        if (agent.isMSIE) {
          var sDomEvents = 'DOMCharacterDataModified DOMSubtreeModified DOMNodeInserted';
          layoutInfo.editable.on(sDomEvents, hChange);
        } else {
          layoutInfo.editable.on('input', hChange);
        }
      }

      // All editor status will be saved on editable with jquery's data
      // for support multiple editor with singleton object.
      layoutInfo.editable.data('callbacks', {
        onChange: options.onChange,
        onAutoSave: options.onAutoSave,
        onImageUpload: options.onImageUpload,
        onImageUploadError: options.onImageUploadError,
        onFileUpload: options.onFileUpload,
        onFileUploadError: options.onFileUpload
      });
    };

    this.detach = function (layoutInfo, options) {
      layoutInfo.editable.off();

      layoutInfo.popover.off();
      layoutInfo.handle.off();
      layoutInfo.dialog.off();

      if (!options.airMode) {
        layoutInfo.dropzone.off();
        layoutInfo.toolbar.off();
        layoutInfo.statusbar.off();
      }
    };
  };

  return EventHandler;
});
