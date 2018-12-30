odoo.define('web_editor.widget', function (require) {
'use strict';

var core = require('web.core');
var ajax = require('web.ajax');
var Widget = require('web.Widget');
var utils = require('web.utils');
var base = require('web_editor.base');
var rte = require('web_editor.rte');

var QWeb = core.qweb;
var range = $.summernote.core.range;
var dom = $.summernote.core.dom;

//////////////////////////////////////////////////////////////////////////////////////////////////////////

var Dialog = Widget.extend({
    events: {
        'hidden.bs.modal': 'destroy',
        'keydown.dismiss.bs.modal': 'stop_escape',
        'click button.save': 'save',
        'click button[data-dismiss="modal"]': 'cancel',
    },
    init: function () {
        this._super();
    },
    start: function () {
        var sup = this._super();
        this.$el.modal({backdrop: 'static'});
        this.$('input:first').focus();
        return sup;
    },
    save: function () {
        this.close();
        this.trigger("saved");
    },
    cancel: function () {
        this.trigger("cancel");
    },
    close: function () {
        this.$el.modal('hide');
    },
    destroy: function () {
        this._super();
        $("body:has('> .modal:visible')").addClass('modal-open');
    },
    stop_escape: function(event) {
        if($(".modal.in").length>0 && event.which == 27){
            event.stopPropagation();
        }
    }
});

/**
 * alt widget. Lets users change a alt & title on a media
 */
var alt = Dialog.extend({
    template: 'web_editor.dialog.alt',
    init: function ($editable, media) {
        this.$editable = $editable;
        this.media = media;
        this.alt = ($(this.media).attr('alt') || "").replace(/&quot;/g, '"');
        this.title = ($(this.media).attr('title') || "").replace(/&quot;/g, '"');
        return this._super();
    },
    save: function () {
        var self = this;
        range.createFromNode(self.media).select();
        this.$editable.data('NoteHistory').recordUndo();
        var alt = this.$('#alt').val();
        var title = this.$('#title').val();
        $(this.media).attr('alt', alt ? alt.replace(/"/g, "&quot;") : null).attr('title', title ? title.replace(/"/g, "&quot;") : null);
        setTimeout(function () {
            click_event(self.media, "mouseup");
        },0);
        return this._super();
    },
});

var click_event = function(el, type) {
    var evt = document.createEvent("MouseEvents");
    evt.initMouseEvent(type, true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
    el.dispatchEvent(evt);
};

/**
 * MediaDialog widget. Lets users change a media, including uploading a
 * new image, font awsome or video and can change a media into an other
 * media
 * 
 * options: select_images: allow the selection of more of one image
 */
var MediaDialog = Dialog.extend({
    template: 'web_editor.dialog.media',
    events : _.extend({}, Dialog.prototype.events, {
        'input input#icon-search': 'search',
    }),
    init: function ($editable, media, options) {
        this._super();
        if ($editable) {
            this.$editable = $editable;
            this.rte = this.$editable.rte || this.$editable.data('rte');
        }
        this.options = options || {};
        this.old_media = media;
        this.media = media;
        this.isNewMedia = !media;
        this.range = range.create();
    },
    start: function () {
        var self = this;

        this.only_images = this.options.only_images || this.options.select_images || (this.media && $(this.media).parent().data("oe-field") === "image");
        if (this.only_images) {
            this.$('[href="#editor-media-document"], [href="#editor-media-video"], [href="#editor-media-icon"]').addClass('hidden');
        }

        if (this.media) {
            if (this.media.nodeName === "IMG") {
                this.$('[href="#editor-media-image"]').tab('show');
            } else if ($(this.media).is('a.o_image')) {
                this.$('[href="#editor-media-document"]').tab('show');
            } else if (this.media.className.match(/(^|\s)media_iframe_video($|\s)/)) {
                this.$('[href="#editor-media-video"]').tab('show');
            } else if (this.media.parentNode.className.match(/(^|\s)media_iframe_video($|\s)/)) {
                this.media = this.media.parentNode;
                this.$('[href="#editor-media-video"]').tab('show');
            } else if (this.media.className.match(/(^|\s)fa($|\s)/)) {
                this.$('[href="#editor-media-icon"]').tab('show');
            }
        }

        this.imageDialog = new ImageDialog(this, this.media, this.options);
        this.imageDialog.appendTo(this.$("#editor-media-image"));
        this.documentDialog = new ImageDialog(this, this.media, _.extend({'document': true}, this.options));
        this.documentDialog.appendTo(this.$("#editor-media-document"));
        if (!this.only_images) {
            this.iconDialog = new fontIconsDialog(this, this.media, this.options);
            this.iconDialog.appendTo(this.$("#editor-media-icon"));
            this.videoDialog = new VideoDialog(this, this.media, this.options);
            this.videoDialog.appendTo(this.$("#editor-media-video"));
        }

        this.active = this.imageDialog;

        $('a[data-toggle="tab"]').on('shown.bs.tab', function (event) {
            if ($(event.target).is('[href="#editor-media-image"]')) {
                self.active = self.imageDialog;
                self.$('li.search, li.previous, li.next').removeClass("hidden");
            } if ($(event.target).is('[href="#editor-media-document"]')) {
                self.active = self.documentDialog;
                self.$('li.search, li.previous, li.next').removeClass("hidden");
            } else if ($(event.target).is('[href="#editor-media-icon"]')) {
                self.active = self.iconDialog;
                self.$('li.search, li.previous, li.next').removeClass("hidden");
                self.$('.nav-tabs li.previous, .nav-tabs li.next').addClass("hidden");
            } else if ($(event.target).is('[href="#editor-media-video"]')) {
                self.active = self.videoDialog;
                self.$('.nav-tabs li.search').addClass("hidden");
            }
        });

        return this._super();
    },
    save: function () {
        if (this.options.select_images) {
            this.trigger("saved", this.active.save());
            this.close();
            return;
        }
        if(this.rte) {
            this.range.select();
            this.rte.historyRecordUndo(this.media);
        }

        var self = this;
        if (self.media) {
            this.media.innerHTML = "";
            if (this.active !== this.imageDialog && this.active !== this.documentDialog) {
                this.imageDialog.clear();
            }
            // if not mode only_images
            if (this.iconDialog && this.active !== this.iconDialog) {
                this.iconDialog.clear();
            }
            if (this.videoDialog && this.active !== this.videoDialog) {
                this.videoDialog.clear();
            }
        } else {
            this.media = document.createElement("img");
            this.range.insertNode(this.media, true);
            this.active.media = this.media;
        }
        this.active.save();

        if (this.active.add_class) {
            $(this.active.media).addClass(this.active.add_class);
        }
        var media = this.active.media;

        $(document.body).trigger("media-saved", [media, self.old_media]);
        self.trigger("saved", [media, self.old_media]);
        setTimeout(function () {
            if (!media.parentNode) {
                return;
            }
            range.createFromNode(media).select();
            click_event(media, "mousedown");
            if (!this.only_images) {
                setTimeout(function () {
                    if($(media).parent().data("oe-field") !== "image") {
                        click_event(media, "click");
                    }
                    click_event(media, "mouseup");
                },0);
            }
        },0);

        this.close();
    },
    searchTimer: null,
    search: function () {
        var self = this;
        var needle = this.$("input#icon-search").val();
        clearTimeout(this.searchTimer);
        this.searchTimer = setTimeout(function () {
            self.active.search(needle || "");
        },250);
    }
});

/**
 * ImageDialog widget. Lets users change an image, including uploading a
 * new image in OpenERP or selecting the image style (if supported by
 * the caller).
 */
var IMAGES_PER_ROW = 6;
var IMAGES_ROWS = 2;
var ImageDialog = Widget.extend({
    template: 'web_editor.dialog.image',
    events: _.extend({}, Dialog.prototype.events, {
        'change .url-source': function (e) {
            this.changed($(e.target));
        },
        'click button.filepicker': function () {
            var filepicker = this.$('input[type=file]');
            if (!_.isEmpty(filepicker)){
                filepicker[0].click();
            }
        },
        'click .js_disable_optimization': function () {
            this.$('input[name="disable_optimization"]').val('1');
            var filepicker = this.$('button.filepicker');
            if (!_.isEmpty(filepicker)){
                filepicker[0].click();
            }
        },
        'change input[type=file]': 'file_selection',
        'submit form': 'form_submit',
        'change input.url': "change_input",
        'keyup input.url': "change_input",
        //'change select.image-style': 'preview_image',
        'click .existing-attachments [data-src]': 'select_existing',
        'click .existing-attachment-remove': 'try_remove',
        'keydown.dismiss.bs.modal': function(){},
    }),
    init: function (parent, media, options) {
        this._super();
        this.options = options || {};
        this.accept = this.options.accept || this.options.document ? "*/*" : "image/*";
        this.domain = this.options.domain || ['|', ['mimetype', '=', false], ['mimetype', this.options.document ? 'not in' : 'in', ['image/gif', 'image/jpe', 'image/jpeg', 'image/jpg', 'image/gif', 'image/png']]];
        this.parent = parent;
        this.old_media = media;
        this.media = media;
        this.images = [];
        this.page = 0;
    },
    start: function () {
        this.$preview = this.$('.preview-container').detach();
        var self = this;
        var res = this._super();
        var o = { url: null, alt: null };

        if ($(this.media).is("img")) {
            o.url = this.media.getAttribute('src');
        } else if ($(this.media).is("a.o_image")) {
            o.url = this.media.getAttribute('href').replace(/[?].*/, '');
            o.id = +o.url.match(/\/web\/content\/([0-9]*)/, '')[1];
        }
        this.parent.$(".pager > li").click(function (e) {
            if(!self.$el.is(':visible')) {
                return;
            }
            e.preventDefault();
            var $target = $(e.currentTarget);
            if ($target.hasClass('disabled')) {
                return;
            }
            self.page += $target.hasClass('previous') ? -1 : 1;
            self.display_attachments();
        });
        this.fetch_existing().then(function () {
            if (o.url) {
                self.set_image(_.find(self.records, function (record) { return record.url === o.url;}) || o);
            }
        });
        return res;
    },
    push: function (attachment) {
        if (this.options.select_images) {
            var img = _.select(this.images, function (v) { return v.id == attachment.id;});
            if (img.length) {
                this.images.splice(this.images.indexOf(img[0]),1);
            }
        } else {
            this.images = [];
        }
        this.images.push(attachment);
    },
    save: function () {
        if (this.options.select_images) {
            this.parent.trigger("save", this.images);
            return this.images;
        }
        this.parent.trigger("save", this.media);

        var img = this.images[0];
        if (!img) {
            return this.media;
        }

        if (!img.is_document) {
            if (this.media.tagName !== "IMG" || !this.old_media) {
                this.add_class = "pull-left";
                this.style = {"width": "100%"};
            }
            if(this.media.tagName !== "IMG") {
                var media = document.createElement('img');
                $(this.media).replaceWith(media);
                this.media = media;
            }
            this.media.setAttribute('src', img.src);
        } else {
            if (this.media.tagName !== "A") {
                $('.note-control-selection').hide();
                var media = document.createElement('a');
                $(this.media).replaceWith(media);
                this.media = media;
            }
            this.media.setAttribute('href', '/web/content/' + img.id + '?unique=' + img.checksum + '&download=true');
            $(this.media).addClass('o_image').attr('title', img.name).attr('data-mimetype', img.mimetype);
        }

        $(this.media).attr('alt', img.alt);
        var style = this.style;
        if (style) { $(this.media).css(style); }

        return this.media;
    },
    clear: function () {
        this.media.className = this.media.className.replace(/(^|\s+)((img(\s|$)|img-(?!circle|rounded|thumbnail))[^\s]*)/g, ' ');
    },
    cancel: function () {
        this.trigger('cancel');
    },
    change_input: function (e) {
        var $input = $(e.target);
        var $button = $input.parent().find("button");
        if ($input.val() === "") {
            $button.addClass("btn-default").removeClass("btn-primary");
        } else {
            $button.removeClass("btn-default").addClass("btn-primary");
        }
    },
    search: function (needle) {
        var self = this;
        this.fetch_existing(needle).then(function () {
            self.selected_existing();
        });
    },
    set_image: function (attachment, error) {
        var self = this;
        this.push(attachment);
        this.$('input.url').val('');
        this.fetch_existing().then(function () {
            self.selected_existing();
        });
    },
    form_submit: function (event) {
        var self = this;
        var $form = this.$('form[action="/web_editor/attachment/add"]');
        if (!$form.find('input[name="upload"]').val().length) {
            var url = $form.find('input[name="url"]').val();
            if (this.selected_existing().size()) {
                event.preventDefault();
                return false;
            }
        }
        $form.find('.well > div').hide().last().after('<span class="fa fa-spin fa-3x fa-refresh"/>');

        var callback = _.uniqueId('func_');
        this.$('input[name=func]').val(callback);
        window[callback] = function (attachments, error) {
            delete window[callback];
            $form.find('.well > span').remove();
            $form.find('.well > div').show();
            _.each(attachments, function (record) {
                record.src = record.url || '/web/image/' + record.id;
                record.is_document = !(/gif|jpe|jpg|png/.test(record.mimetype));
            });
            if (error || !attachments.length) {
                self.file_selected(null, error || !attachments.length);
            }
            self.images = attachments;
            for (var i=0; i<attachments.length; i++) {
                self.file_selected(attachments[i], error);
            }
        };
    },
    file_selection: function () {
        this.$el.addClass('nosave');
        this.$('form').removeClass('has-error').find('.help-block').empty();
        this.$('button.filepicker').removeClass('btn-danger btn-success');
        this.$('form').submit();
    },
    file_selected: function(attachment, error) {
        var $button = this.$('button.filepicker');
        if (!error) {
            $button.addClass('btn-success');
            this.set_image(attachment);
        } else {
            this.$('form').addClass('has-error')
                .find('.help-block').text(error);
            $button.addClass('btn-danger');
        }

        if (!this.options.select_images) {
            // auto save and close popup
            this.parent.save();
        }
    },
    fetch_existing: function (needle) {
        var domain = [['res_model', '=', 'ir.ui.view']].concat(this.domain);
        if (needle && needle.length) {
            domain.push('|', ['datas_fname', 'ilike', needle], ['name', 'ilike', needle]);
        }
        return ajax.jsonRpc('/web/dataset/call_kw', 'call', {
            model: 'ir.attachment',
            method: 'search_read',
            args: [],
            kwargs: {
                domain: domain,
                fields: ['name', 'mimetype', 'checksum', 'url'], // if we want to use /web/image/xxx with redirect for image url, remove 'url'
                order: 'id desc',
                context: base.get_context()
            }
        }).then(this.proxy('fetched_existing'));
    },
    fetched_existing: function (records) {
        this.records = records;
        _.each(records, function (record) {
            record.src = record.url || '/web/image/' + record.id;
            record.is_document = !(/gif|jpe|jpg|png/.test(record.mimetype));
        });
        this.display_attachments();
    },
    display_attachments: function () {
        var self = this;
        var per_screen = IMAGES_PER_ROW * IMAGES_ROWS;
        var from = this.page * per_screen;
        var records = this.records;

        // Create rows of 3 records
        var rows = _(records).chain()
            .slice(from, from + per_screen)
            .groupBy(function (_, index) { return Math.floor(index / IMAGES_PER_ROW); })
            .values()
            .value();

        this.$('.help-block').empty();

        this.$('.existing-attachments').replaceWith(
            QWeb.render(
                'web_editor.dialog.image.existing.content', {rows: rows}));
        this.parent.$('.pager')
            .find('li.previous').toggleClass('disabled', (from === 0)).end()
            .find('li.next').toggleClass('disabled', (from + per_screen >= records.length));

        this.$el.find('.o_image').each(function () {
            var $div = $(this);
            if (/gif|jpe|jpg|png/.test($div.data('mimetype'))) {
                var $img = $('<img/>').addClass('img img-responsive').attr('src', $div.data('url') || $div.data('src'));
                $div.addClass('o_webimage').append($img);
            }
        });
        this.selected_existing();
    },
    select_existing: function (e) {
        var $img = $(e.currentTarget);
        var attachment = _.find(this.records, function (record) { return record.id === $img.data('id'); });
        this.push(attachment);
        this.selected_existing();
    },
    selected_existing: function () {
        var self = this;
        this.$('.existing-attachment-cell.media_selected').removeClass("media_selected");
        var $select = this.$('.existing-attachment-cell [data-src]').filter(function () {
            var $img = $(this);
            return !!_.find(self.images, function (v) {
                return (v.url === $img.data("src") || ($img.data("url") && v.url === $img.data("url")) || v.id === $img.data("id"));
            });
        });
        $select.closest('.existing-attachment-cell').addClass("media_selected");
        return $select;
    },
    try_remove: function (e) {
        var $help_block = this.$('.help-block').empty();
        var self = this;
        var $a = $(e.target);
        var id = parseInt($a.data('id'), 10);
        var attachment = _.findWhere(this.records, {id: id});
        var $both = $a.parent().children();

        $both.css({borderWidth: "5px", borderColor: "#f00"});

        return ajax.jsonRpc('/web_editor/attachment/remove', 'call', {'ids': [id]}).then(function (prevented) {
            if (_.isEmpty(prevented)) {
                self.records = _.without(self.records, attachment);
                self.display_attachments();
                return;
            }
            $both.css({borderWidth: "", borderColor: ""});
            $help_block.replaceWith(QWeb.render(
                'web_editor.dialog.image.existing.error', {
                    views: prevented[id]
                }
            ));
        });
    },
});


var cacheCssSelectors = {};
var getCssSelectors = function(filter) {
    var css = [];
    if (cacheCssSelectors[filter]) {
        return cacheCssSelectors[filter];
    }
    var sheets = document.styleSheets;
    for(var i = 0; i < sheets.length; i++) {
        var rules;
        // try...catch because browser may not able to enumerate rules for cross-domain stylesheets
        try {
            rules = sheets[i].rules || sheets[i].cssRules;
        } catch(e) {
            console.warn("Can't read the css rules of: " + sheets[i].href, e);
            continue;
        }
        if (rules) {
            for(var r = 0; r < rules.length; r++) {
                var selectorText = rules[r].selectorText;
                if (selectorText) {
                    selectorText = selectorText.split(/\s*,\s*/);
                    var data = null;
                    for(var s = 0; s < selectorText.length; s++) {
                        var match = selectorText[s].match(filter);
                        if (match) {
                            var clean = match[1].slice(1).replace(/::?before$/, '');
                            if (!data) {
                                data = [match[1], rules[r].cssText.replace(/(^.*\{\s*)|(\s*\}\s*$)/g, ''), clean, [clean]];
                            } else {
                                data[0] += (", " + match[1]);
                                data[3].push(clean);
                            }
                        }
                    }
                    if (data) {
                        css.push(data);
                    }
                }
            }
        }
    }
    return cacheCssSelectors[filter] = css;
};
var computeFonts = _.once(function() {
    _.each(fontIcons, function (data) {
        data.cssData = getCssSelectors(data.parser);
        data.alias = [];
        data.icons = _.map(data.cssData, function (css) {
            data.alias.push.apply(data.alias, css[3]);
            return css[2];
        });
    });
});

rte.Class.include({
    init: function (EditorBar) {
        this._super.apply(this, arguments);
        computeFonts();
    },
    onEnableEditableArea: function ($editable) {
        if ($editable.data('oe-type') === "monetary") {
            $editable.attr('contenteditable', false);
            $editable.find('.oe_currency_value').attr('contenteditable', true);
        }
        if ($editable.is('[data-oe-model]') && !$editable.is('[data-oe-model="ir.ui.view"]') && !$editable.is('[data-oe-type="html"]')) {
            $editable.data('layoutInfo').popover().find('.btn-group:not(.note-history)').remove();
        }
    },
});

/* list of font icons to load by editor. The icons are displayed in the media editor and
 * identified like font and image (can be colored, spinned, resized with fa classes).
 * To add font, push a new object {base, parser}
 * - base: class who appear on all fonts (eg: fa fa-refresh)
 * - parser: regular expression used to select all font in css style sheets
 */
var fontIcons = [{'base': 'fa', 'parser': /(?=^|\s)(\.fa-[0-9a-z_-]+::?before)/i}];


/**
 * FontIconsDialog widget. Lets users change a font awsome, suport all
 * font awsome loaded in the css files.
 */
var fontIconsDialog = Widget.extend({
    template: 'web_editor.dialog.font-icons',
    events : _.extend({}, Dialog.prototype.events, {
        'click .font-icons-icon': function (e) {
            e.preventDefault();
            e.stopPropagation();

            this.$('#fa-icon').val(e.target.getAttribute('data-id'));
            $(".font-icons-icon").removeClass("font-icons-selected");
            $(e.target).addClass("font-icons-selected");
        },
        'keydown.dismiss.bs.modal': function(){},
    }),

    // extract list of font (like awsome) from the cheatsheet.
    renderElement: function() {
        this.iconsParser = fontIcons;
        this.icons = _.flatten(_.map(fontIcons, function (data) {
                return data.icons;
            }));
        this._super();
    },

    init: function (parent, media) {
        this._super();
        this.parent = parent;
        this.media = media;
        computeFonts();
    },
    start: function () {
        return this._super().then(this.proxy('load_data'));
    },
    search: function (needle) {
        var iconsParser = this.iconsParser;
        if (needle) {
            var iconsParser = [];
            _.filter(this.iconsParser, function (data) {
                var cssData = _.filter(data.cssData, function (cssData) {
                    return _.find(cssData[3], function (alias) {
                        return alias.indexOf(needle) !== -1;
                    });
                });
                if (cssData.length) {
                    iconsParser.push({
                        base: data.base,
                        cssData: cssData
                    });
                }
            });
        }
        this.$('div.font-icons-icons').html(
            QWeb.render('web_editor.dialog.font-icons.icons', {'iconsParser': iconsParser}));
    },
    /**
     * Removes existing FontAwesome classes on the bound element, and sets
     * all the new ones if necessary.
     */
    save: function () {
        var self = this;
        this.parent.trigger("save", this.media);
        var icons = this.icons;
        var style = this.media.attributes.style ? this.media.attributes.style.value : '';
        var classes = (this.media.className||"").split(/\s+/);
        var custom_classes = /^fa(-[1-5]x|spin|rotate-(9|18|27)0|flip-(horizont|vertic)al|fw|border)?$/;
        var non_fa_classes = _.reject(classes, function (cls) {
            return self.getFont(cls) || custom_classes.test(cls);
        });
        var final_classes = non_fa_classes.concat(this.get_fa_classes());
        if (this.media.tagName !== "SPAN") {
            var media = document.createElement('span');
            $(media).data($(this.media).data());
            $(this.media).replaceWith(media);
            this.media = media;
            style = style.replace(/\s*width:[^;]+/, '');
        }
        $(this.media).attr("class", _.compact(final_classes).join(' ')).attr("style", style);
    },
    /**
     * return the data font object (with base, parser and icons) or null
     */
    getFont: function (classNames) {
        if (!(classNames instanceof Array)) {
            classNames = (classNames||"").split(/\s+/);
        }
        var fontIcon, cssData;
        for (var k=0; k<this.iconsParser.length; k++) {
            fontIcon = this.iconsParser[k];
            for (var s=0; s<fontIcon.cssData.length; s++) {
                cssData = fontIcon.cssData[s];
                if (_.intersection(classNames, cssData[3]).length) {
                    return {
                        'base': fontIcon.base,
                        'parser': fontIcon.parser,
                        'icons': fontIcon.icons,
                        'font': cssData[2]
                    };
                }
            }
        }
        return null;
    },

    /**
     * Looks up the various FontAwesome classes on the bound element and
     * sets the corresponding template/form elements to the right state.
     * If multiple classes of the same category are present on an element
     * (e.g. fa-lg and fa-3x) the last one occurring will be selected,
     * which may not match the visual look of the element.
     */
    load_data: function () {
        var classes = (this.media&&this.media.className||"").split(/\s+/);
        for (var i = 0; i < classes.length; i++) {
            var cls = classes[i];
            switch(cls) {
                case 'fa-1x':case 'fa-2x':case 'fa-3x':case 'fa-4x':case 'fa-5x':
                    // size classes
                    this.$('#fa-size').val(cls);
                    continue;
                case 'fa-spin':
                case 'fa-rotate-90':case 'fa-rotate-180':case 'fa-rotate-270':
                case 'fa-flip-horizontal':case 'fa-rotate-vertical':
                    this.$('#fa-rotation').val(cls);
                    continue;
                case 'fa-fw':
                    continue;
                case 'fa-border':
                    this.$('#fa-border').prop('checked', true);
                    continue;
                case '': continue;
                default:
                    $(".font-icons-icon").removeClass("font-icons-selected").filter("[data-alias*=',"+cls+",']").addClass("font-icons-selected");
                    for (var k=0; k<this.icons.length; k++) {
                        if (this.icons.indexOf(cls) !== -1) {
                            this.$('#fa-icon').val(cls);
                            break;
                        }
                    }
            }
        }
    },
    /**
     * Serializes the dialog to an array of FontAwesome classes. Includes
     * the base ``fa``.
     */
    get_fa_classes: function () {
        var font = this.getFont(this.$('#fa-icon').val());
        return [
            font ? font.base : 'fa',
            font ? font.font : "",
            this.$('#fa-size').val(),
            this.$('#fa-rotation').val(),
            this.$('#fa-border').prop('checked') ? 'fa-border' : ''
        ];
    },
    clear: function () {
        this.media.className = this.media.className.replace(/(^|\s)(fa(\s|$)|fa-[^\s]*)/g, ' ');
    },
});


function createVideoNode(url, options) {
    options = options || {};

    // video url patterns(youtube, instagram, vimeo, dailymotion, youku)
    var ytRegExp = /^(?:(?:https?:)?\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$/;
    var ytMatch = url.match(ytRegExp);

    var igRegExp = /\/\/instagram.com\/p\/(.[a-zA-Z0-9]*)/;
    var igMatch = url.match(igRegExp);

    var vRegExp = /\/\/vine.co\/v\/(.[a-zA-Z0-9]*)/;
    var vMatch = url.match(vRegExp);

    var vimRegExp = /\/\/(player.)?vimeo.com\/([a-z]*\/)*([0-9]{6,11})[?]?.*/;
    var vimMatch = url.match(vimRegExp);

    var dmRegExp = /.+dailymotion.com\/(video|hub)\/([^_]+)[^#]*(#video=([^_&]+))?/;
    var dmMatch = url.match(dmRegExp);

    var youkuRegExp = /\/\/v\.youku\.com\/v_show\/id_(\w+)\.html/;
    var youkuMatch = url.match(youkuRegExp);

    var $video = $('<iframe>');
    if (ytMatch && ytMatch[1].length === 11) {
      var youtubeId = ytMatch[1];
      $video = $('<iframe>')
        .attr('src', '//www.youtube.com/embed/' + youtubeId)
        .attr('width', '640').attr('height', '360');
    } else if (igMatch && igMatch[0].length) {
      $video = $('<iframe>')
        .attr('src', igMatch[0] + '/embed/')
        .attr('width', '612').attr('height', '710')
        .attr('scrolling', 'no')
        .attr('allowtransparency', 'true');
    } else if (vMatch && vMatch[0].length) {
      $video = $('<iframe>')
        .attr('src', vMatch[0] + '/embed/simple')
        .attr('width', '600').attr('height', '600')
        .attr('class', 'vine-embed');
    } else if (vimMatch && vimMatch[3].length) {
      $video = $('<iframe webkitallowfullscreen mozallowfullscreen allowfullscreen>')
        .attr('src', '//player.vimeo.com/video/' + vimMatch[3])
        .attr('width', '640').attr('height', '360');
    } else if (dmMatch && dmMatch[2].length) {
      $video = $('<iframe>')
        .attr('src', '//www.dailymotion.com/embed/video/' + dmMatch[2])
        .attr('width', '640').attr('height', '360');
    } else if (youkuMatch && youkuMatch[1].length) {
      $video = $('<iframe webkitallowfullscreen mozallowfullscreen allowfullscreen>')
        .attr('height', '498')
        .attr('width', '510')
        .attr('src', '//player.youku.com/embed/' + youkuMatch[1]);
    } else {
      // this is not a known video link. Now what, Cat? Now what?
          $video = $('<iframe webkitallowfullscreen mozallowfullscreen allowfullscreen>')
            .attr('width', '640')
            .attr('height', '360')
            .attr('src', url);
    }

    if (options.autoplay) {
        $video.attr("src", $video.attr("src") + "?autoplay=1");
    }

    $video.attr('frameborder', 0);

    return $video;
}

/**
 * VideoDialog widget. Lets users change a video, support all summernote
 * video, and embled iframe
 */
var VideoDialog = Widget.extend({
    template: 'web_editor.dialog.video',
    events : _.extend({}, Dialog.prototype.events, {
        'click input#urlvideo ~ button': 'get_video',
        'click input#embedvideo ~ button': 'get_embed_video',
        'change input#autoplay': 'get_video',
        'change input#urlvideo': 'change_input',
        'keyup input#urlvideo': 'change_input',
        'change input#embedvideo': 'change_input',
        'keyup input#embedvideo': 'change_input',
        'keydown.dismiss.bs.modal': function(){},
    }),
    init: function (parent, media) {
        this._super();
        this.parent = parent;
        this.media = media;
    },
    start: function () {
        this.$preview = this.$('.preview-container').detach();
        this.$iframe = this.$("iframe");
        var $media = $(this.media);
        if ($media.hasClass("media_iframe_video")) {
            var src = $media.data('src');
            this.$("input#urlvideo").val(src);
            this.$("input#autoplay").prop("checked", (src || "").indexOf("autoplay") >= 0);
            this.get_video();
        }
        return this._super();
    },
    change_input: function (e) {
        var $input = $(e.target);
        var $button = $input.parent().find("button");
        if ($input.val() === "") {
            $button.addClass("btn-default").removeClass("btn-primary");
        } else {
            $button.removeClass("btn-default").addClass("btn-primary");
        }
    },
    get_embed_video: function (event) {
        event.preventDefault();
        var embedvideo = this.$("input#embedvideo").val().match(/src=["']?([^"']+)["' ]?/);
        if (embedvideo) {
            this.$("input#urlvideo").val(embedvideo[1]);
            this.get_video(event);
        }
        return false;
    },
    get_video: function (event) {
        if (event) event.preventDefault();
        var $video = createVideoNode(this.$("input#urlvideo").val(), {autoplay: this.$("input#autoplay").is(":checked")});
        this.$iframe.replaceWith($video);
        this.$iframe = $video;
        return false;
    },
    save: function () {
        this.parent.trigger("save", this.media);
        var video_id = this.$("#video_id").val();
        if (!video_id) {
            this.$("button.btn-primary").click();
            video_id = this.$("#video_id").val();
        }
        var video_type = this.$("#video_type").val();
        var $iframe = $(
            '<div class="media_iframe_video" data-src="'+this.$iframe.attr("src")+'">'+
                '<div class="css_editable_mode_display">&nbsp;</div>'+
                '<div class="media_iframe_video_size" contentEditable="false">&nbsp;</div>'+
                '<iframe src="'+this.$iframe.attr("src")+'" frameborder="0" allowfullscreen="allowfullscreen" contentEditable="false"></iframe>'+
            '</div>');
        $(this.media).replaceWith($iframe);
        this.media = $iframe[0];
    },
    clear: function () {
        if (this.media.dataset.src) {
            try {
                delete this.media.dataset.src;
            } catch(e) {
                this.media.dataset.src = undefined;
            }
        }
        this.media.className = this.media.className.replace(/(^|\s)media_iframe_video(\s|$)/g, ' ');
    },
});

/* ----- EDITOR: LINK & MEDIA ---- */
var LinkDialog = Dialog.extend({
    template: 'web_editor.dialog.link',
    events: _.extend({}, Dialog.prototype.events, {
        'change :input.url-source': 'changed',
        'keyup :input.url': 'onkeyup',
        'keyup :input': 'preview',
        'click button.remove': 'remove_link',
        'change input#link-text': function (e) {
            this.text = $(e.target).val();
        },
        'change .link-style': function (e) {
            this.preview();
        },
    }),
    init: function (editable, linkInfo) {
        this._super(editable, linkInfo);
        this.editable = editable;
        this.data = linkInfo || {};

        this.data.className = "";
        if (this.data.range) {
            this.data.iniClassName = $(this.data.range.sc).filter("a").attr("class") || "";
            this.data.className = this.data.iniClassName.replace(/(^|\s+)btn(-[a-z0-9_-]*)?/gi, ' ');

            var is_link = this.data.range.isOnAnchor();
            var r = this.data.range;

            var sc = r.sc;
            var so = r.so;
            var ec = r.ec;
            var eo = r.eo;

            var nodes;
            if (!is_link) {
                if (sc.tagName) {
                    sc = dom.firstChild(so ? sc.childNodes[so] : sc);
                    so = 0;
                } else if (so !== sc.textContent.length) {
                    if (sc === ec) {
                        ec = sc = sc.splitText(so);
                        eo -= so;
                    } else {
                        sc = sc.splitText(so);
                    }
                    so = 0;
                }
                if (ec.tagName) {
                    ec = dom.lastChild(eo ? ec.childNodes[eo-1] : ec);
                    eo = ec.textContent.length;
                } else if (eo !== ec.textContent.length) {
                    ec.splitText(eo);
                }
                
                nodes = dom.listBetween(sc, ec);

                // browsers can't target a picture or void node
                if (dom.isVoid(sc) || dom.isImg(sc)) {
                  so = dom.listPrev(sc).length-1;
                  sc = sc.parentNode;
                }
                if (dom.isBR(ec)) {
                  eo = dom.listPrev(ec).length-1;
                  ec = ec.parentNode;
                } else if (dom.isVoid(ec) || dom.isImg(sc)) {
                  eo = dom.listPrev(ec).length;
                  ec = ec.parentNode;
                }

                this.data.range = range.create(sc, so, ec, eo);
                this.data.range.select();
            } else {
                nodes = dom.ancestor(sc, dom.isAnchor).childNodes;
            }

            if (dom.isImg(sc) && nodes.indexOf(sc) === -1) {
                nodes.push(sc);
            }
            if (nodes.length > 1 || dom.ancestor(nodes[0], dom.isImg)) {
                var text = "";
                this.data.images = [];
                for (var i=0; i<nodes.length; i++) {
                    if (dom.ancestor(nodes[i], dom.isImg)) {
                        this.data.images.push(dom.ancestor(nodes[i], dom.isImg));
                        text += '[IMG]';
                    } else if (!is_link && nodes[i].nodeType === 1) {
                        // just use text nodes from listBetween
                    } else if (!is_link && i===0) {
                        text += nodes[i].textContent.slice(so, Infinity);
                    } else if (!is_link && i===nodes.length-1) {
                        text += nodes[i].textContent.slice(0, eo);
                    } else {
                        text += nodes[i].textContent;
                    }
                }
                this.data.text = text;
            }
        }

        this.data.text = this.data.text.replace(/[ \t\r\n]+/g, ' ');
    },
    start: function () {
        this.bind_data();
        this.$('input.url-source:eq(1)').closest('.list-group-item').addClass('active');
        return this._super();
    },
    get_data: function (test) {
        var self = this;
        var def = new $.Deferred();
        var $e = this.$('.active input.url-source');
        if (!$e.length) {
            $e = this.$('input.url-source:first');
        }
        $e.closest('.form-group').removeClass('has-error');
        var val = $e.val();
        var label = this.$('#link-text').val() || val;

        if (label && this.data.images) {
            for(var i=0; i<this.data.images.length; i++) {
                label = label.replace(/</, "&lt;").replace(/>/, "&gt;").replace(/\[IMG\]/, this.data.images[i].outerHTML);
            }
        }

        if (!test && (!val || !$e[0].checkValidity())) {
            // FIXME: error message
            $e.closest('.form-group').addClass('has-error');
            $e.focus();
            def.reject();
        }

        var style = this.$("input[name='link-style-type']:checked").val() || '';
        var size = this.$("input[name='link-style-size']:checked").val() || '';
        var classes = (this.data.className || "") + (style && style.length ? " btn " : "") + style + " " + size;
        var isNewWindow = this.$('input.window-new').prop('checked');
        if ($e.hasClass('email-address') && (_.str.startsWith(val, 'mailto:') || (val.indexOf("@") !== -1 && !_.str.startsWith(val, 'http') && !_.str.startsWith(val, 'www')))) {
            self.get_data_buy_mail(def, $e, isNewWindow, label, classes, test);
        } else {
            self.get_data_buy_url(def, $e, isNewWindow, label, classes, test);
        }
        return def;
    },
    get_data_buy_mail: function (def, $e, isNewWindow, label, classes, test) {
        var val = $e.val();
        if (utils.is_email(val, true)) {
            def.resolve(val.indexOf("mailto:") === 0 ? val : 'mailto:' + val, isNewWindow, label, classes);
        } else {
            $e.closest('.form-group').addClass('has-error');
            $e.focus();
            def.reject();
        }
    },
    get_data_buy_url: function (def, $e, isNewWindow, label, classes, test) {
        def.resolve($e.val(), isNewWindow, label, classes);
    },
    save: function () {
        var self = this;
        var _super = this._super.bind(this);
        return this.get_data()
            .then(function (url, new_window, label, classes) {
                self.data.url = url;
                self.data.isNewWindow = new_window;
                self.data.text = label;
                self.data.className = classes.replace(/\s+/gi, ' ').replace(/^\s+|\s+$/gi, '');

                self.trigger("save", self.data);
            }).then(_super);
    },
    bind_data: function () {
        var href = this.data.url;
        var new_window = this.data.isNewWindow;
        var text = this.data.text;
        var classes = this.data.iniClassName;

        this.$('input#link-text').val(text);
        this.$('input.window-new').prop('checked', new_window);

        if (classes) {
            this.$('input[value!=""]').each(function () {
                var $option = $(this);
                if (classes.indexOf($option.val()) !== -1) {
                    $option.attr("checked", "checked");
                }
            });
        }

        if (href) {
            var match;
            if(match = /mailto:(.+)/.exec(href)) {
                this.$('input.email-address').val(match = /mailto:(.+)/.exec(href) ? match[1] : '');
            } else {
                this.$('input.url').val(href);
            }
        }
        this.preview();
    },
    changed: function (e) {
        $(e.target).closest('.list-group-item')
            .addClass('active')
            .siblings().removeClass('active')
            .addBack().removeClass('has-error');
        this.preview();
    },
    onkeyup: function (e) {
        var $e = $(e.target);
        var is_link = ($e.val()||'').length && $e.val().indexOf("@") === -1;
        this.$('input.window-new').closest("div").toggle(is_link);
        this.preview();
    },
    preview: function () {
        var $preview = this.$("#link-preview");
        this.get_data(true).then(function (url, new_window, label, classes) {
            $preview.attr("target", new_window ? '_blank' : "")
                .attr("href", url && url.length ? url : "#")
                .html((label && label.length ? label : url))
                .attr("class", classes.replace(/pull-\w+/, ''));
        });
    }
});

return {
    'getCssSelectors': getCssSelectors,
    'Dialog': Dialog,
    'alt': alt,
    'MediaDialog': MediaDialog,
    'fontIcons': fontIcons,
    'LinkDialog': LinkDialog
};

});
