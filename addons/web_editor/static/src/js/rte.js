odoo.define('web_editor.rte', function (require) {
'use strict';

var ajax = require('web.ajax');
var core = require('web.core');
var utils = require('web.utils');
var Widget = require('web.Widget');
var summernote = require('web_editor.summernote');
var base = require('web_editor.base');

var _t = core._t;

//////////////////////////////////////////////////////////////////////////////////////////////////////////
/* Summernote Lib (neek change to make accessible: method and object) */

var dom = summernote.core.dom;
var range = summernote.core.range;

//////////////////////////////////////////////////////////////////////////////////////////////////////////
/* Change History to have a global History for all summernote instances */

var History = function History ($editable) {
    var aUndo = [];
    var pos = 0;

    this.makeSnap = function (event, rng) {
        rng = rng || range.create();
        var elEditable = $(rng && rng.sc).closest('.o_editable')[0];
        if (!elEditable) {
            return false;
        }
        return {
            event: event,
            editable: elEditable,
            contents: elEditable.innerHTML,
            bookmark: rng && rng.bookmark(elEditable),
            scrollTop: $(elEditable).scrollTop()
        };
    };

    this.applySnap = function (oSnap) {
        var $editable = $(oSnap.editable);

        if (!!document.documentMode) {
            $editable.removeAttr("contentEditable").removeProp("contentEditable");
        }

        $editable.html(oSnap.contents).scrollTop(oSnap.scrollTop);
        $(".oe_overlay").remove();
        $(".note-control-selection").hide();

        $editable.trigger("content_changed");

        try {
            var r = oSnap.editable.innerHTML === "" ? range.create(oSnap.editable, 0) : range.createFromBookmark(oSnap.editable, oSnap.bookmark);
            r.select();
        } catch(e) {
            console.error(e);
            return;
        }

        $(document).trigger("click");
        $(".o_editable *").filter(function () {
            var $el = $(this);
            if($el.data('snippet-editor')) {
                $el.removeData();
            }
        });


        setTimeout(function () {
            var target = dom.isBR(r.sc) ? r.sc.parentNode : dom.node(r.sc);
            if (!target) {
                return;
            }

            $editable.trigger("applySnap");

            var evt = document.createEvent("MouseEvents");
            evt.initMouseEvent("click", true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, target);
            target.dispatchEvent(evt);

            $editable.trigger("keyup");
        },0);
    };

    this.undo = function () {
        if (!pos) { return; }
        var _toSnap = toSnap;
        if (_toSnap) {
            this.saveSnap();
        }
        if (!aUndo[pos] && (!aUndo[pos] || aUndo[pos].event !== 'undo')) {
            var temp = this.makeSnap('undo');
            if (temp && (!pos || temp.contents !== aUndo[pos-1].contents)) {
                aUndo[pos] = temp;
            } else {
               pos--;
            }
        } else if (_toSnap) {
            pos--;
        }
        this.applySnap(aUndo[Math.max(--pos,0)]);
        while (pos && (aUndo[pos].event === "blur" || (aUndo[pos+1].editable ===  aUndo[pos].editable && aUndo[pos+1].contents ===  aUndo[pos].contents))) {
            this.applySnap(aUndo[--pos]);
        }
    };
    this.hasUndo = function () {
        return (toSnap && (toSnap.event !== "blur" && toSnap.event !== "activate" && toSnap.event !== "undo")) ||
            !!_.find(aUndo.slice(0, pos+1), function (undo) {
                return undo.event !== "blur" && undo.event !== "activate" && undo.event !== "undo";
            });
    };

    this.getEditableHasUndo = function () {
        var editable = [];
        if ((toSnap && (toSnap.event !== "blur" && toSnap.event !== "activate" && toSnap.event !== "undo"))) {
            editable.push(toSnap.editable);
        }
        _.each(aUndo.slice(0, pos+1), function (undo) {
            if (undo.event !== "blur" && undo.event !== "activate" && undo.event !== "undo") {
                editable.push(undo.editable);
            }
        });
        return _.uniq(editable);
    };

    this.redo = function () {
        if (!aUndo[pos+1]) { return; }
        this.applySnap(aUndo[++pos]);
        while (aUndo[pos+1] && aUndo[pos].event === "active") {
            this.applySnap(aUndo[pos++]);
        }
    };
    this.hasRedo = function () {
        return aUndo.length > pos+1;
    };

    var toSnap, split;
    this.recordUndo = function ($editable, event, internal_history) {
        var self = this;
        if (!$editable) {
            var rng = range.create();
            if(!rng) return;
            $editable = $(rng.sc).closest(".o_editable");
        }

        if (aUndo[pos] && (event === "applySnap" || event === "activate")) {
            return;
        }

        if (!internal_history) {
            if (!event || !toSnap || !aUndo[pos-1] || toSnap.event === "activate") { // don't trigger change for all keypress
                setTimeout(function () {
                    $editable.trigger("content_changed");
                },0);
            }
        }

        if (aUndo[pos]) {
            pos = Math.min(pos, aUndo.length);
            aUndo.splice(pos, aUndo.length);
        }

        // => make a snap when the user change editable zone (because: don't make snap for each keydown)
        if (toSnap && (toSnap.split || !event || toSnap.event !== event || toSnap.editable !== $editable[0])) {
            this.saveSnap();
        }

        if (pos && aUndo[pos-1].editable !== $editable[0]) {
            var snap = this.makeSnap('blur', range.create(aUndo[pos-1].editable, 0));
            pos++;
            aUndo.push(snap);
        }

        if (range.create()) {
            toSnap = self.makeSnap(event);
        } else {
            toSnap = false;
        }
    };

    this.splitNext = function () {
        if (toSnap) {
            toSnap.split = true;
        }
    };

    this.saveSnap = function () {
        if (toSnap) {
            if (!aUndo[pos]) {
                pos++;
            }
            aUndo.push(toSnap);
            delete toSnap.split;
            toSnap = null;
        }
    };
};
var history = new History();

//////////////////////////////////////////////////////////////////////////////////////////////////////////
// add focusIn to jQuery to allow to move caret into a div of a contentEditable area

$.extend($.expr[':'],{
    o_editable: function(node,i,m){
        while (node) {
            if (node.className && _.isString(node.className)) {
                if (node.className.indexOf('o_not_editable')!==-1 ) {
                    return false;
                }
                if (node.className.indexOf('o_editable')!==-1 ) {
                    return true;
                }
            }
            node = node.parentNode;
        }
        return false;
    }
});

$.fn.extend({
    focusIn: function () {
        if (this.length) {
            range.create(dom.firstChild(this[0]), 0).select();
        }
        return this;
    },
    focusInEnd: function () {
        if (this.length) {
            var last = dom.lastChild(this[0]);
            range.create(last, dom.nodeLength(last)).select();
        }
        return this;
    },
    selectContent: function () {
        if (this.length) {
            var next = dom.lastChild(this[0]);
            range.create(dom.firstChild(this[0]), 0, next, next.textContent.length).select();
        }
        return this;
    }
});

//////////////////////////////////////////////////////////////////////////////////////////////////////////

/* ----- RICH TEXT EDITOR ---- */

var RTE = Widget.extend({
    init: function (EditorBar, config) {
        var self = this;
        this.EditorBar = EditorBar;
        data.rte = this;
        this._super.apply(this, arguments);

        this.init_bootstrap_carousel = $.fn.carousel;
        this.edit_bootstrap_carousel = function () {
            var res = self.init_bootstrap_carousel.apply(this, arguments);
            // off bootstrap keydown event to remove event.preventDefault()
            // and allow to change cursor position
            $(this).off('keydown.bs.carousel');
            return res;
        };

        if (config) {
            this.config = config;
        }
    },
    /**
     * Add a record undo to history
     * @param {DOM} target where the dom is changed is editable zone
     */
    historyRecordUndo: function ($target, event, internal_history) {
        $target = $($target);
        var rng = range.create();
        var $editable = $(rng && rng.sc).closest(".o_editable");
        if (!rng || !$editable.length) {
            $editable = $target.closest(".o_editable");
            rng = range.create($target.closest("*")[0],0);
        } else {
            rng = $editable.data('range') || rng;
        }
        try {
            // TODO this line might break for unknown reasons. I suppose that
            // the created range is an invalid one. As it might be tricky to
            // adapt that line and that it is not a critical one, temporary fix
            // is to ignore the errors that this generates.
            rng.select();
        } catch (e) {
            console.log('error', e);
        }
        history.recordUndo($editable, event, internal_history);
    },
    /**
     * Makes the page editable
     *
     * @param {Boolean} [restart=false] in case the edition was already set
     *                                  up once and is being re-enabled.
     * @returns {$.Deferred} deferred indicating when the RTE is ready
     */
    start: function () {
        var self = this;

        this.saving_mutex = new utils.Mutex();

        $.fn.carousel = this.edit_bootstrap_carousel;

        this._onKeydown = _.bind(this.onKeydown, this);
        $(document).on('keydown', this, this._onKeydown);
        this._onMousedown = _.bind(this.onMousedown, this);
        $(document).on('mousedown activate', this, this._onMousedown);
        this._onMouseup = _.bind(this.onMouseup, this);
        $(document).on('mouseup', this, this._onMouseup);

        $('.o_not_editable').attr("contentEditable", false);

        var $editable = this.editable();

        $editable.addClass('o_editable').data('rte', self);

        $editable.each(function () {
            var $node = $(this);

            // add class to display inline-block for empty t-field
            if(window.getComputedStyle(this).display === "inline" && $node.data('oe-type') !== "image") {
                $node.addClass('o_is_inline_editable');
            }

            $node.data('initInnerHTML', $node.html());
        });

        // start element observation
        $(document).on('content_changed', '.o_editable', function (ev) {
            self.trigger('change', this);
            if (!ev.__isDirtyHandled) {
                $(this).addClass('o_dirty');
                ev.__isDirtyHandled = true;
            }
        });

        this._onClick = _.bind(this.onClick, this);
        $('#wrapwrap, .o_editable').on('click', '*', this, this._onClick);

        $('body').addClass("editor_enable");

        $(document)
            .tooltip({
                selector: '[data-oe-readonly]',
                container: 'body',
                trigger: 'hover',
                delay: { "show": 1000, "hide": 100 },
                placement: 'bottom',
                title: _t("Readonly field")
            })
            .on('click', function () {
                $(this).tooltip('hide');
            });

        $(document).trigger('mousedown');
        self.trigger('rte:start');
    },

    save: function (context) {
        var self = this;

        this.__saved = {}; // list of allready saved views and data

        var editables = history.getEditableHasUndo();

        $('.o_editable')
            .destroy()
            .removeClass('o_editable o_is_inline_editable');

        var defs = $('.o_dirty')
            .removeAttr('contentEditable')
            .removeClass('o_dirty oe_carlos_danger o_is_inline_editable')
            .map(function () {
                var $el = $(this);

                $el.find('[class]').filter(function () {
                    if (!this.getAttribute('class').match(/\S/)) {
                        this.removeAttribute('class');
                    }
                });

                // TODO: Add a queue with concurrency limit in webclient
                // https://github.com/medikoo/deferred/blob/master/lib/ext/function/gate.js
                return self.saving_mutex.exec(function () {
                    return self.saveElement($el, context)
                        .then(undefined, function (thing, response) {
                            // because ckeditor regenerates all the dom,
                            // we can't just setup the popover here as
                            // everything will be destroyed by the DOM
                            // regeneration. Add markings instead, and
                            // returns a new rejection with all relevant
                            // info
                            var id = _.uniqueId('carlos_danger_');
                            $el.addClass('o_dirty oe_carlos_danger ' + id);
                            return $.Deferred().reject({
                                id: id,
                                error: response.data,
                            });
                        });
                });
            }).get();

        return $.when.apply(null, defs).then(function () {
            window.onbeforeunload = null;
        }, function (failed) {
            // If there were errors, re-enable edition
            self.stop();
            self.start();
            // jquery's deferred being a pain in the ass
            if (!_.isArray(failed)) { failed = [failed]; }

            _(failed).each(function (failure) {
                var html = failure.error.exception_type === "except_osv";
                if (html) {
                    var msg = $("<div/>").text(failure.error.message).html();
                    var data = msg.substring(3,msg.length-2).split(/', u'/);
                    failure.error.message = '<b>' + data[0] + '</b>' + data[1];
                }
                $('.o_editable.' + failure.id)
                    .removeClass(failure.id)
                    .popover({
                        html: html,
                        trigger: 'hover',
                        content: failure.error.message,
                        placement: 'auto top',
                    })
                    // Force-show popovers so users will notice them.
                    .popover('show');
            });
        });
    },

    /**
     * Get HTML cloned element with text nodes escaped for XML storage
     */
    getEscapedElement: function($el) {
        var escaped_el = $el.clone();
        var to_escape = escaped_el.find('*').addBack();
        to_escape = to_escape.not(to_escape.filter('object,iframe,script,style,[data-oe-model][data-oe-model!="ir.ui.view"]').find('*').addBack());
        to_escape.contents().each(function(){
            if(this.nodeType == 3) {
                this.nodeValue = $('<div />').text(this.nodeValue).html();
            }
        });
        return escaped_el;
    },

    saveElement: function ($el, context) {
        // remove multi edition
        if ($el.data('oe-model')) {
            var key =  $el.data('oe-model')+":"+$el.data('oe-id')+":"+$el.data('oe-field')+":"+$el.data('oe-type')+":"+$el.data('oe-expression')+":"+$el.data('oe-xpath');
            if (this.__saved[key]) return true;
            this.__saved[key] = true;
        }
        var markup = this.getEscapedElement($el).prop('outerHTML');

        return ajax.jsonRpc('/web/dataset/call', 'call', {
            model: 'ir.ui.view',
            method: 'save',
            args: [
                $el.data('oe-id'),
                markup,
                $el.data('oe-xpath') || null,
                _.omit(context || base.get_context(), 'lang')
            ],
        });
    },

    stop: function () {
        if (this.$last) {
            this.$last.destroy();
            this.$last = null;
        }

        $.fn.carousel = this.init_bootstrap_carousel;

        $(document).off('keydown', this._onKeydown);
        $(document).off('mousedown applySnap', this._onMousedown);
        $(document).off('mouseup', this._onMouseup);
        $('.o_not_editable').removeAttr("contentEditable");
        $(document).off('content_changed').removeClass('o_is_inline_editable').removeData('rte');
        $('#wrapwrap, .o_editable').off('click', this._onClick);
        $(document).tooltip('destroy');
        $('body').removeClass("editor_enable");
        this.trigger('rte:stop');
    },

    cancel: function () {
        $('.o_editable').each(function () {
            var $node = $(this);
            $node.data('initInnerHTML', $node.html());
        });
        this.stop();
    },

    onClick: function (event) {
        event.preventDefault();
    },

    // handler for cancel editor
    onKeydown: function (event) {
        if (event.keyCode === 27 && !$('.modal-content:visible').length) {
            setTimeout(function () {
                $('#editor-top-navbar [data-action="cancel"]').click();
                var $modal = $('.modal-content > .modal-body').parents(".modal:first");
                $modal.off('keyup.dismiss.bs.modal');
                setTimeout(function () {
                    $modal.on('keyup.dismiss.bs.modal', function () {
                        $(this).modal('hide');
                    });
                },500);
            },0);
        }
    },

    // activate editor
    onMousedown: function (event) {
        var $target = $(event.target);
        var $editable = $target.closest('.o_editable');

        if (!$editable.size()) {
            return;
        }

        if ($target.is('a')) {
            // add contenteditable on link to improve its editing behaviour
            $target.attr('contenteditable', true);
            setTimeout(function () {
                $editable.not($target).attr('contenteditable', false);
            });
            // once clicked outside, remove contenteditable on link
            var reactive_editable = function(e){
                if($target.is(e.target)) {
                    return;
                }
                $target.removeAttr('contenteditable');
                $editable.attr('contenteditable', true);
                $(document).off('mousedown', reactive_editable);
            }
            $(document).on('mousedown', reactive_editable);
        }

        if (this && this.$last && (!$editable.size() || this.$last[0] != $editable[0])) {
            var $destroy = this.$last;
            history.splitNext();

            setTimeout(function () {
                var id = $destroy.data('note-id');
                $destroy.destroy().removeData('note-id').removeAttr('data-note-id');
                $('#note-popover-'+id+', #note-handle-'+id+', #note-dialog-'+id+'').remove();
            },150); // setTimeout to remove flickering when change to editable zone (re-create an editor)
            this.$last = null;
        }
        if ($editable.size() && (!this.$last || this.$last[0] != $editable[0]) &&
                ($target.closest('[contenteditable]').attr('contenteditable') || "").toLowerCase() !== 'false') {

            $editable.summernote(this.config($editable));

            $editable.data('NoteHistory', history);
            this.$last = $editable;

            // firefox & IE fix
            try {
                document.execCommand('enableObjectResizing', false, false);
                document.execCommand('enableInlineTableEditing', false, false);
                document.execCommand( '2D-position', false, false);
            } catch (e) {}
            document.body.addEventListener('resizestart', function (evt) {evt.preventDefault(); return false;});
            document.body.addEventListener('movestart', function (evt) {evt.preventDefault(); return false;});
            document.body.addEventListener('dragstart', function (evt) {evt.preventDefault(); return false;});

            if (!range.create()) {
                $editable.focusIn();
            }

            if (dom.isImg($target[0])) {
                $target.trigger('mousedown'); // for activate selection on picture
            }

            this.onEnableEditableArea($editable);
        }
    },

    onEnableEditableArea: function ($editable) {
    },

    onMouseup: function (ev) {
        var $target = $(ev.target);
        var $editable = $target.closest('.o_editable');

        if (!$editable.size()) {
            return;
        }

        var self = this;
        setTimeout(function () {
            self.historyRecordUndo($target, 'activate',  true);
        },0);

        // Browsers select different content from one to another after a
        // triple click (especially: if triple-clicking on a paragraph on
        // Chrome, blank characters of the element following the paragraph are
        // selected too)
        //
        // The triple click behavior is reimplemented for all browsers here
        if (ev.originalEvent.detail === 3) {
            // Select the whole content inside the deepest DOM element that was
            // triple-clicked
            range.create(ev.target, 0, ev.target, ev.target.childNodes.length).select();
        }
    },

    editable: function () {
        return $('#wrapwrap [data-oe-model]')
            .not('.o_not_editable')
            .filter(function () {
                return !$(this).closest('.o_not_editable').length;
            })
            .not('link, script')
            .not('[data-oe-readonly]')
            .not('img[data-oe-field="arch"], br[data-oe-field="arch"], input[data-oe-field="arch"]')
            .not('.oe_snippet_editor')
            .add('.o_editable');
    },

    config: function ($editable) {
        return {
            'airMode' : true,
            'focus': false,
            'airPopover': [
                ['style', ['style']],
                ['font', ['bold', 'italic', 'underline', 'clear']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['table', ['table']],
                ['insert', ['link', 'picture']],
                ['history', ['undo', 'redo']],
            ],
            'styleWithSpan': false,
            'inlinemedia' : ['p'],
            'lang': "odoo",
            'onChange': function (html, $editable) {
                $editable.trigger("content_changed");
            }
        };
    },
});


var data = {
    'history': history,
    'Class': RTE
};
return data;

});
