odoo.define('web_editor.wysiwyg.plugin.link', function (require) {
'use strict';

var core = require('web.core');
var LinkDialog = require('wysiwyg.widgets.LinkDialog');
var Plugins = require('web_editor.wysiwyg.plugins');
var registry = require('web_editor.wysiwyg.plugin.registry');

var _t = core._t;
var dom = $.summernote.dom;
dom.isAnchor = function (node) {
    return (node.tagName === 'A' || node.tagName === 'BUTTON' || $(node).hasClass('btn')) &&
        !$(node).hasClass('fa') && !$(node).hasClass('o_image');
};

//--------------------------------------------------------------------------
// link
//--------------------------------------------------------------------------

var LinkPlugin = Plugins.linkDialog.extend({
    events: {
        'dblclick .note-editable': '_onDblclick',
    },

    //--------------------------------------------------------------------------
    // Public summernote module API
    //--------------------------------------------------------------------------

    /**
     * @param {Object} layoutInfo
     */
    show: function () {
        var self = this;
        var linkInfo = this.context.invoke('editor.getLinkInfo');
        this.context.invoke('editor.saveRange');
        return this.showLinkDialog(linkInfo)
            .then(function (linkInfo) {})
            .guardedCatch(function () {});
    },
    /**
     * @override
     * @param {Object} linkInfo
     * @returns {Promise}
     */
    showLinkDialog: function (linkInfo) {
        var self = this;
        this.context.invoke('editor.hidePopover');
        var media = this.context.invoke('editor.restoreTarget');

        if (linkInfo.range) {
            var r = linkInfo.range.getPoints();

            // move carret in icon, video...
            if (!media && (dom.ancestor(r.sc, dom.isImg) || dom.ancestor(r.sc, dom.isIcon))) {
                media = dom.ancestor(r.sc, dom.isImg) || dom.ancestor(r.sc, dom.isIcon);
            }
            // if select a text content in anchor then click on image then click on anchor button
            if (dom.isImg(media) || dom.isIcon(media)) {
                r.sc = media.parentNode;
                r.so = [].indexOf.call(media.parentNode.childNodes, media);
                r.ec = media;
                r.eo = dom.nodeLength(media);

                linkInfo.range.sc = r.sc;
                linkInfo.range.so = r.so;
                linkInfo.range.ec = r.ec;
                linkInfo.range.eo = r.eo;
            }

            linkInfo.isAnchor = linkInfo.range.isOnAnchor();
            linkInfo.className = linkInfo.isAnchor ? dom.ancestor(r.sc, dom.isAnchor).className : '';
            linkInfo.url = linkInfo.isAnchor ? ($(dom.ancestor(r.sc, dom.isAnchor)).attr('href') || '').replace(window.location.origin, '') : '';

            var nodes = [];
            if (linkInfo.isAnchor) {
                nodes = dom.ancestor(r.sc, dom.isAnchor).childNodes;
            } else if (!linkInfo.range.isCollapsed()) {
                if (dom.isImg(media) || dom.isIcon(media)) {
                    nodes.push(media);
                } else {
                    if (r.sc.tagName) {
                        r.sc = (r.so ? r.sc.childNodes[r.so] : r.sc).firstChild || r.sc;
                        r.so = 0;
                    } else if (r.so !== r.sc.textContent.length) {
                        if (r.sc === r.ec) {
                            r.ec = r.sc = r.sc.splitText(r.so);
                            r.eo -= r.so;
                        } else {
                            r.sc = r.sc.splitText(r.so);
                        }
                        r.so = 0;
                    }
                    if (r.ec.tagName) {
                        r.ec = (r.eo ? r.ec.childNodes[r.eo - 1] : r.ec).lastChild || r.ec;
                        r.eo = r.ec.textContent.length;
                    } else if (r.eo !== r.ec.textContent.length) {
                        r.ec.splitText(r.eo);
                    }

                    // browsers can't target a picture or void node
                    if (dom.isVoid(r.sc) || dom.isImg(r.sc)) {
                        r.so = dom.listPrev(r.sc).length - 1;
                        r.sc = r.sc.parentNode;
                    }
                    if (dom.isBR(r.ec)) {
                        r.eo = dom.listPrev(r.ec).length - 1;
                        r.ec = r.ec.parentNode;
                    } else if (dom.isVoid(r.ec) || dom.isImg(r.sc)) {
                        r.eo = dom.listPrev(r.ec).length;
                        r.ec = r.ec.parentNode;
                    }
                    linkInfo.range.sc = r.sc;
                    linkInfo.range.so = r.so;
                    linkInfo.range.ec = r.ec;
                    linkInfo.range.eo = r.eo;
                    linkInfo.range.select();
                    this.context.invoke('editor.saveRange');
                    linkInfo.range = this.context.invoke('editor.createRange');

                    // search nodes to insert in the anchor

                    var startPoint = this.context.invoke('HelperPlugin.makePoint', r.sc, r.so);
                    var endPoint = this.context.invoke('HelperPlugin.makePoint', r.ec, r.eo);
                    dom.walkPoint(startPoint, endPoint, function (point) {
                        var node = point.node.childNodes && point.node.childNodes[point.offset] || point.node;
                        nodes.push(node);
                    });

                    nodes = _.filter(_.uniq(nodes), function (node) {
                        return nodes.indexOf(node.parentNode) === -1;
                    });
                }
            }

            if (nodes.length > 0) {
                var text = "";
                linkInfo.images = [];
                for (var i = 0; i < nodes.length; i++) {
                    if (dom.ancestor(nodes[i], dom.isImg)) {
                        text += dom.ancestor(nodes[i], dom.isImg).outerHTML;
                    } else if (dom.ancestor(nodes[i], dom.isIcon)) {
                        text += dom.ancestor(nodes[i], dom.isIcon).outerHTML;
                    } else if (!linkInfo.isAnchor && nodes[i].nodeType === 1) {
                        // just use text nodes from listBetween
                    } else if (!linkInfo.isAnchor && i === 0) {
                        text += nodes[i].textContent;
                    } else if (!linkInfo.isAnchor && i === nodes.length - 1) {
                        text += nodes[i].textContent;
                    } else {
                        text += nodes[i].textContent;
                    }
                }
                linkInfo.text = text.replace(this.context.invoke('HelperPlugin.getRegex', 'space', 'g'), ' ');
            }

            linkInfo.needLabel = !linkInfo.text.length;
        }

        var def = new Promise(function (resolve, reject) {
            var linkDialog = new LinkDialog(self.options.parent, {
                    onClose: function () {
                        setTimeout(function () {
                            self.context.invoke('editor.focus');
                        });
                    }
                },
                _.omit(linkInfo, 'range')
            );

            linkDialog.on('save', self, self._wrapCommand(function (newLinkInfo) {
                var isCollapsed = linkInfo.range.isCollapsed();
                linkInfo.range.select();
                newLinkInfo.range = linkInfo.range;

                var $anchor;
                if (linkInfo.isAnchor) {
                    $anchor = $(dom.ancestor(r.sc, dom.isAnchor));
                    $anchor.css(newLinkInfo.style || {});
                    if (newLinkInfo.isNewWindow) {
                        $anchor.attr('target', '_blank');
                    } else {
                        $anchor.removeAttr('target');
                    }
                } else {
                    self.context.invoke('editor.saveRange');
                    self.context.invoke('editor.createLink', newLinkInfo);
                    var range = self.context.invoke('editor.createRange');
                    var anchor = dom.ancestor(range.sc.childNodes[range.so] || range.sc, dom.isAnchor);
                    $anchor = $(anchor);
                    if (isCollapsed) {
                        // move the range just after the link
                        var point = dom.nextPoint({
                            node: anchor,
                            offset: dom.nodeLength(anchor),
                        });
                        range = self.context.invoke('editor.setRange', point.node, point.offset);
                        range.select();
                    } else {
                        $anchor.selectContent();
                    }
                }
                if ((dom.isImg(media) || dom.isIcon(media)) && !$anchor.find(media).length) {
                    $(media).remove();
                }
                $anchor.attr('class', newLinkInfo.className);
                $anchor.attr('href', newLinkInfo.url);
                self.context.invoke('editor.saveRange');
                self.context.invoke('editor.saveTarget', $anchor[0]);
                self.context.triggerEvent('focusnode', $anchor[0]);
                resolve(linkInfo);
            }));
            linkDialog.on('closed', self, function () {
                this.context.invoke('editor.restoreRange');
                this.context.invoke('LinkPopover.update');
                reject();
            });
            linkDialog.open();
        });
        return def;
    },
    /**
     * Remove the current link, keep its contents.
     *
     * @override
     */
    unlink: function () {
        var rng = this.context.invoke('editor.createRange');
        var anchor = rng.sc;
        while (anchor && anchor.tagName !== 'A') {
            anchor = anchor.parentElement;
        }
        if (!anchor) {
            this.context.invoke('editor.hidePopover');
            return;
        }
        var startAndEndInvisible = this.context.invoke('HelperPlugin.getRegex', 'startAndEndInvisible', 'g');
        anchor.innerHTML = anchor.innerHTML.replace(startAndEndInvisible, '');
        var $contents = $(anchor).contents();
        $(anchor).before($contents).remove();

        this.context.invoke('editor.hidePopover');

        var start = $contents[0];
        var end = $contents.last()[0];
        rng = this.context.invoke('editor.setRange', start, 0, end, dom.nodeLength(end));
        rng.select();
        this.editable.normalize();
        this.context.invoke('editor.saveRange');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _addButtons: function () {
        var self = this;
        this._super();

        this.context.memo('help.LinkPlugin.show', this.options.langInfo.help['linkDialog.show']);

        this.context.memo('button.linkPlugin', function () {
            return self.context.invoke('buttons.button', {
                contents: self.ui.icon(self.options.icons.link),
                tooltip: self.lang.link.link + self.context.invoke('buttons.representShortcut', 'LinkPlugin.show'),
                click: self.context.createInvokeHandler('LinkPlugin.show')
            }).render();
        });
    },
    /**
     * @param {jQueryEvent} e
     */
    _onDblclick: function (e) {
        if (dom.ancestor(e.target, dom.isAnchor) && !dom.isMedia(e.target)) {
            this.show();
        }
    },
});

var LinkPopover = Plugins.linkPopover.extend({

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Prevent links without text: replace empty text with the word "Label".
     *
     * @param {DOM} anchor
     * @param {bool} select
     */
    fillEmptyLink: function (anchor, select) {
        if (dom.isAnchor(anchor)) {
            var text = _t('Label');
            if (this.context.invoke('HelperPlugin.getRegex', 'onlyEmptySpace').test(anchor.innerHTML)) {
                $(anchor).contents().remove();
                $(anchor).append(this.document.createTextNode(text));
            }
            var rng = this.context.invoke('editor.createRange');
            if (select && anchor.innerHTML === text) {
                this._cleanLastLink();
                rng.sc = rng.ec = anchor.firstChild;
                rng.so = 0;
                rng.eo = dom.nodeLength(rng.sc);
                rng.select();
                this.context.invoke('editor.saveRange');
            }
            if (select) {
                this.lastAnchor = anchor;
            }
        }
    },
    /**
     * @override
     */
    hide: function () {
        this._cleanLastLink();
        this._super();
    },
    /**
     * @override
     */
    update: function () {
        var rng = this.context.invoke('editor.createRange');
        var anchor = dom.ancestor(rng.sc, dom.isAnchor);
        if (anchor && anchor === dom.ancestor(rng.ec, dom.isAnchor)) {
            anchor = dom.ancestor(rng.sc, dom.isAnchor);
            if (!$(anchor).is(':o_editable')) {
                this.hide();
                return;
            }
        } else {
            anchor = false;
        }

        if ($(anchor).data('toggle') === 'tab') {
            anchor = false;
        }

        if (!this.options.displayPopover(anchor)) {
            anchor = false;
        }

        if (anchor !== this.lastAnchor) {
            this._cleanLastLink();
        }

        if (!anchor) {
            this.hide();
            return;
        }

        if (dom.isAnchor(anchor)) {
            this.lastAnchor = anchor;
        }


        var $target = $(anchor);
        if (!$target.data('show_tooltip') && this.context.options.tooltip) {
            $target.data('show_tooltip', true);
            setTimeout(function () {
                $target.tooltip({
                    title: _t('Double-click to edit'),
                    trigger: 'manual',
                    container: this.document.body,
                    placement: 'top'
                }).tooltip('show');
                setTimeout(function () {
                    $target.tooltip('dispose');
                }, 2000);
            }, 400);
        }

        var innerHTML = anchor.innerHTML.replace('&nbsp;', '\u00A0').replace('&#8203;', '\u200B');

        // prevent links without text
        this.fillEmptyLink(anchor, true);

        // add invisible char to prevent the carret to leave the link at the begin or end
        if (innerHTML[0] !== '\u200B') {
            var before = this.document.createTextNode('\u200B');
            $(anchor).prepend(before);
        }
        if (innerHTML[innerHTML.length - 1] !== '\u200B') {
            var after = this.document.createTextNode('\u200B');
            $(anchor).append(after);
        }

        anchor.normalize();

        var href = $(anchor).attr('href');
        this.$popover.find('a').attr('href', href).html(href);

        var pos = $(anchor).offset();
        var posContainer = $(this.options.container).offset();
        pos.left = pos.left - posContainer.left + 10;
        pos.top = pos.top - posContainer.top + $(anchor).outerHeight();

        this.$popover.css({
            display: 'block',
            left: pos.left,
            top: pos.top,
        });

        this.context.layoutInfo.editor.after(this.$popover);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Clean the last link and prevent links without text.
     *
     * @private
     */
    _cleanLastLink: function () {
        if (this.lastAnchor) {
            this.fillEmptyLink(this.lastAnchor);

            var range = this.context.invoke('editor.createRange');
            var rangeChange;
            var innerHTML = this.lastAnchor.innerHTML.replace('&nbsp;', '\u00A0').replace('&#8203;', '\u200B');
            // prevent links without text
            if (
                this.$editable.has(this.lastAnchor).length &&
                this.context.invoke('HelperPlugin.getRegexBlank', {
                    space: true,
                    invisible: true,
                    nbsp: true,
                }).test(innerHTML)
            ) {
                $(this.lastAnchor).contents().remove();
                $(this.lastAnchor).append(this.document.createTextNode(_t('Label')));
                range.sc = range.ec = this.lastAnchor.firstChild;
                range.so = 0;
                range.eo = dom.nodeLength(range.sc);
                rangeChange = true;
            }
            var firstChild = this.context.invoke('HelperPlugin.firstLeaf', this.lastAnchor);
            if (
                !firstChild.tagName &&
                this.context.invoke('HelperPlugin.getRegex', 'startInvisible').test(firstChild.textContent)
            ) {
                firstChild.textContent = firstChild.textContent.replace(this.context.invoke('HelperPlugin.getRegex', 'startInvisible'), '');
                if (range.sc === firstChild && range.so) {
                    range.so -= 1;
                    rangeChange = true;
                }
                if (range.ec === firstChild && range.eo) {
                    range.eo -= 1;
                    rangeChange = true;
                }
            }
            var lastChild = this.context.invoke('HelperPlugin.lastLeaf', this.lastAnchor);
            if (
                lastChild.textContent.length > 1 &&
                !lastChild.tagName &&
                this.context.invoke('HelperPlugin.getRegex', 'endInvisible').test(lastChild.textContent)
            ) {
                lastChild.textContent = lastChild.textContent.replace(this.context.invoke('HelperPlugin.getRegex', 'endInvisible'), '');
                if (range.sc === lastChild && range.so > dom.nodeLength(lastChild)) {
                    range.so = dom.nodeLength(lastChild);
                    rangeChange = true;
                }
                if (range.ec === lastChild && range.eo > dom.nodeLength(lastChild)) {
                    range.eo = dom.nodeLength(lastChild);
                    rangeChange = true;
                }
            }
            if (rangeChange) {
                range.select();
                this.context.invoke('editor.saveRange');
            }
            this.lastAnchor = null;
        }
    },
});

registry.add('LinkPlugin', LinkPlugin)
    .add('LinkPopover', LinkPopover)
    .add('linkDialog', null)
    .add('linkPopover', null)
    .add('autoLink', null);

return {
    LinkPlugin: LinkPlugin,
    LinkPopover: LinkPopover,
};

});
