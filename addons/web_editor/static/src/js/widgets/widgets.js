odoo.define('web_editor.widget', function (require) {
'use strict';

var core = require('web.core');
var Dialog = require('web.Dialog');
var Widget = require('web.Widget');
var utils = require('web.utils');
var weContext = require("web_editor.context");

var QWeb = core.qweb;
var range = $.summernote.core.range;
var dom = $.summernote.core.dom;

var _t = core._t;

/**
 * Extend Dialog class to handle save/cancel of edition components.
 */
Dialog = Dialog.extend({
    init: function (parent, options) {
        options = options || {};
        this._super(parent, _.extend({}, {
            buttons: [
                {text: options.save_text || _t("Save"), classes: "btn-primary o_save_button", click: this.save},
                {text: _t("Discard"), close: true}
            ]
        }, options));

        this.destroyAction = "cancel";

        var self = this;
        this.opened().then(function () {
            self.$('input:first').focus();
        });
        this.on("closed", this, function () {
            this.trigger(this.destroyAction, this.final_data || null);
        });
    },
    save: function () {
        this.destroyAction = "save";
        this.close();
    },
});

/**
 * alt widget. Lets users change a alt & title on a media
 */
var alt = Dialog.extend({
    template: 'web_editor.dialog.alt',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/editor.xml']
    ),

    init: function (parent, options, $editable, media) {
        this._super(parent, _.extend({}, {
            title: _t("Change media description and tooltip")
        }, options));
        this.$editable = $editable;
        this.media = media;
        this.alt = ($(this.media).attr('alt') || "").replace(/&quot;/g, '"');
        this.title = ($(this.media).attr('title') || "").replace(/&quot;/g, '"');
    },
    save: function () {
        range.createFromNode(this.media).select();
        this.$editable.data('NoteHistory').recordUndo();
        var alt = this.$('#alt').val();
        var title = this.$('#title').val();
        $(this.media).attr('alt', alt ? alt.replace(/"/g, "&quot;") : null).attr('title', title ? title.replace(/"/g, "&quot;") : null);
        _.defer((function () {
            click_event(this.media, "mouseup");
        }).bind(this));
        return this._super.apply(this, arguments);
    },
});

function click_event(el, type) {
    var evt = document.createEvent("MouseEvents");
    evt.initMouseEvent(type, true, true, window, 0, 0, 0, 0, 0, false, false, false, false, 0, el);
    el.dispatchEvent(evt);
}

/**
 * ImageDialog widget. Let users change an image, including uploading a
 * new image in odoo or selecting the image style (if supported by
 * the caller).
 */
var ImageDialog = Widget.extend({
    template: 'web_editor.dialog.image',
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],
    IMAGES_PER_ROW: 6,
    IMAGES_ROWS: 2,
    events: _.extend({}, Dialog.prototype.events, {
        'change .url-source': function (e) {
            this.changed($(e.target));
        },
        'click button.filepicker': function () {
            var filepicker = this.$('input[type=file]');
            if (!_.isEmpty(filepicker)) {
                filepicker[0].click();
            }
        },
        'click .js_disable_optimization': function () {
            this.$('input[name="disable_optimization"]').val('1');
            var filepicker = this.$('button.filepicker');
            if (!_.isEmpty(filepicker)) {
                filepicker[0].click();
            }
        },
        'change input[type=file]': 'file_selection',
        'submit form': 'form_submit',
        'change input.url': "change_input",
        'keyup input.url': "change_input",
        'click .existing-attachments [data-src]': 'select_existing',
        'dblclick .existing-attachments [data-src]': function (e) {
            this.select_existing(e, true);
            this.getParent().save();
        },
        'click .o_existing_attachment_remove': 'try_remove',
        'keydown.dismiss.bs.modal': function () {},
    }),
    init: function (parent, media, options) {
        this._super.apply(this, arguments);
        this.options = options || {};
        this.accept = this.options.accept || this.options.document ? "*/*" : "image/*";
        if (options.domain) {
            this.domain = typeof options.domain === 'function' ? options.domain() : options.domain;
        } else if (options.res_id) {
            this.domain = ['|',
                '&', ['res_model', '=', options.res_model], ['res_id', '=', options.res_id],
                ['res_model', '=', 'ir.ui.view']];
        } else {
            this.domain = [['res_model', '=', 'ir.ui.view']];
        }
        this.parent = parent;
        this.old_media = media;
        this.media = media;
        this.images = [];
        this.page = 0;
    },
    start: function () {
        this.$preview = this.$('.preview-container').detach();
        var self = this;
        var res = this._super.apply(this, arguments);
        var o = {url: null, alt: null};

        if ($(this.media).is("img")) {
            o.url = this.media.getAttribute('src');
        } else if ($(this.media).is("a.o_image")) {
            o.url = this.media.getAttribute('href').replace(/[?].*/, '');
            o.id = +o.url.match(/\/web\/content\/([0-9]*)/, '')[1];
        }
        this.parent.$(".pager > li").click(function (e) {
            if (!self.$el.is(':visible')) {
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
    push: function (attachment, force_select) {
        if (this.options.select_images) {
            var img = _.select(this.images, function (v) { return v.id === attachment.id; });
            if (img.length) {
                if (!force_select) {
                  this.images.splice(this.images.indexOf(img[0]),1);
                }
            } else {
                this.images.push(attachment);
            }
        } else {
            this.images = [attachment];
        }
    },
    save: function () {
        var self = this;
        if (this.options.select_images) {
            return this.images;
        }

        var img = this.images[0];
        if (!img) {
            return this.media;
        }

        var def = $.when();
        if (!img.access_token) {
            def = this._rpc({
                model: 'ir.attachment',
                method: 'generate_access_token',
                args: [[img.id]]
            }).then(function (access_token) {
                img.access_token = access_token[0];
            });
        }

        return def.then(function () {
            var media;
            if (!img.is_document) {
                if (img.access_token && self.options.res_model !== 'ir.ui.view') {
                    img.src += _.str.sprintf('?access_token=%s', img.access_token);
                }
                if (self.media.tagName !== "IMG" || !self.old_media) {
                    self.add_class = "pull-left";
                    self.style = {"width": "100%"};
                }
                if (self.media.tagName !== "IMG") {
                    media = document.createElement('img');
                    $(self.media).replaceWith(media);
                    self.media = media;
                }
                self.media.setAttribute('src', img.src);
            } else {
                if (self.media.tagName !== "A") {
                    $('.note-control-selection').hide();
                    media = document.createElement('a');
                    $(self.media).replaceWith(media);
                    self.media = media;
                }
                var href = '/web/content/' + img.id + '?';
                if (img.access_token && self.options.res_model !== 'ir.ui.view') {
                    href += _.str.sprintf('access_token=%s&', img.access_token);
                }
                href += 'unique=' + img.checksum + '&download=true';
                self.media.setAttribute('href', href);
                $(self.media).addClass('o_image').attr('title', img.name).attr('data-mimetype', img.mimetype);
            }

            $(self.media).attr('alt', img.alt);
            var style = self.style;
            if (style) { $(self.media).css(style); }

            if (self.options.onUpload) {
                // We consider that when selecting an image it is as if we upload it in the html content.
                self.options.onUpload([img]);
            }

            return self.media;
        });
    },
    clear: function () {
        this.media.className = this.media.className.replace(/(^|\s+)((img(\s|$)|img-(?!circle|rounded|thumbnail))[^\s]*)/g, ' ');
    },
    change_input: function (e) {
        var $input = $(e.target);
        var $button = $input.parent().find("button");
        var emptyValue = ($input.val() === "");
        $button.toggleClass("btn-default", emptyValue).toggleClass("btn-primary", !emptyValue);
    },
    search: function (needle) {
        var self = this;
        this.fetch_existing(needle).then(function () {
            self.selected_existing();
        });
    },
    set_image: function (attachment) {
        this.push(attachment);
        this.$('input.url').val('');
        this.search();
    },
    form_submit: function (event) {
        var self = this;
        var $form = this.$('form[action="/web_editor/attachment/add"]');
        if (!$form.find('input[name="upload"]').val().length) {
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
                record.src = record.url || _.str.sprintf('/web/image/%s/%s', record.id, encodeURI(record.name)); // Name is added for SEO purposes
                record.is_document = !(/gif|jpe|jpg|png/.test(record.mimetype));
            });
            if (error || !attachments.length) {
                self.file_selected(null, error || !attachments.length);
            }
            self.images = attachments;
            for (var i=0; i<attachments.length; i++) {
                self.file_selected(attachments[i], error);
            }

            if (self.options.onUpload) {
                self.options.onUpload(attachments);
            }
        };
    },
    file_selection: function () {
        var $form = this.$('form');
        this.$el.addClass('nosave');
        $form.removeClass('has-error').find('.help-block').empty();
        this.$('button.filepicker').removeClass('btn-danger btn-success');
        $form.submit();
    },
    file_selected: function (attachment, error) {
        var $button = this.$('button.filepicker');
        if (!error) {
            $button.addClass('btn-success');
            this.set_image(attachment);
        } else {
            this.$('form').addClass('has-error').find('.help-block').text(error);
            $button.addClass('btn-danger');
        }

        if (!this.options.select_images) {
            this.parent.save(); // auto save and close popup
        }
    },
    fetch_existing: function (needle) {
        var domain = this.domain.concat(['|', ['mimetype', '=', false], ['mimetype', this.options.document ? 'not in' : 'in', ['image/gif', 'image/jpe', 'image/jpeg', 'image/jpg', 'image/gif', 'image/png']]]);
        if (needle && needle.length) {
            domain.push('|', ['datas_fname', 'ilike', needle], ['name', 'ilike', needle]);
        }
        return this._rpc({
            model: 'ir.attachment',
            method: 'search_read',
            args: [],
            kwargs: {
                domain: domain,
                fields: ['name', 'mimetype', 'checksum', 'url', 'type', 'res_id', 'res_model', 'access_token'],
                order: [{name: 'id', asc: false}],
                context: weContext.get(),
            }
        }).then(this.proxy('fetched_existing'));
    },
    fetched_existing: function (records) {
        this.records = _.uniq(_.filter(records, function (r) {
            return (r.type === "binary" || r.url && r.url.length > 0);
        }), function (r) {
            return (r.url || r.id);
        });
        _.each(this.records, function (record) {
            record.src = record.url || _.str.sprintf('/web/image/%s/%s', record.id, encodeURI(record.name)); // Name is added for SEO purposes
            record.is_document = !(/gif|jpe|jpg|png/.test(record.mimetype));
        });
        this.display_attachments();
    },
    display_attachments: function () {
        var self = this;
        var per_screen = this.IMAGES_PER_ROW * this.IMAGES_ROWS;
        var from = this.page * per_screen;
        var records = this.records;

        // Create rows of 3 records
        var rows = _(records).chain()
            .slice(from, from + per_screen)
            .groupBy(function (_, index) { return Math.floor(index / self.IMAGES_PER_ROW); })
            .values()
            .value();

        this.$('.help-block').empty();

        this.$('.existing-attachments').replaceWith(QWeb.render('web_editor.dialog.image.existing.content', {rows: rows}));
        this.parent.$('.pager')
            .find('li.previous a').toggleClass('disabled', (from === 0)).end()
            .find('li.next a').toggleClass('disabled', (from + per_screen >= records.length));

        this.$el.find('.o_image').each(function () {
            var $div = $(this);
            if (/gif|jpe|jpg|png/.test($div.data('mimetype'))) {
                var $img = $('<img/>').addClass('img img-responsive').attr('src', $div.data('url') || $div.data('src'));
                $div.addClass('o_webimage').append($img);
            }
        });
        this.selected_existing();
    },
    select_existing: function (e, force_select) {
        var $img = $(e.currentTarget);
        var attachment = _.find(this.records, function (record) { return record.id === $img.data('id'); });
        this.push(attachment, force_select);
        this.selected_existing();
    },
    selected_existing: function () {
        var self = this;
        this.$('.o_existing_attachment_cell.o_selected').removeClass("o_selected");
        var $select = this.$('.o_existing_attachment_cell [data-src]').filter(function () {
            var $img = $(this);
            return !!_.find(self.images, function (v) {
                return (v.url === $img.data("src") || ($img.data("url") && v.url === $img.data("url")) || v.id === $img.data("id"));
            });
        });
        $select.closest('.o_existing_attachment_cell').addClass("o_selected");
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

        return this._rpc({
            route: '/web_editor/attachment/remove',
            params: {
                ids: [id],
            },
        }).then(function (prevented) {
            if (_.isEmpty(prevented)) {
                self.records = _.without(self.records, attachment);
                self.display_attachments();
                return;
            }
            $both.css({borderWidth: "", borderColor: ""});
            $help_block.replaceWith(QWeb.render('web_editor.dialog.image.existing.error', {
                views: prevented[id]
            }));
        });
    },
});

/**
 *  list of font icons to load by editor. The icons are displayed in the media editor and
 * identified like font and image (can be colored, spinned, resized with fa classes).
 * To add font, push a new object {base, parser}
 *
 * - base: class who appear on all fonts (eg: fa fa-refresh)
 * - parser: regular expression used to select all font in css style sheets
 *
 * @type Array
 */
var fontIcons = [{'base': 'fa', 'parser': /(?=^|\s)(\.fa-[0-9a-z_-]+::?before)/i}];

var cacheCssSelectors = {};
var getCssSelectors = function (filter) {
    var css = [];
    if (cacheCssSelectors[filter]) {
        return cacheCssSelectors[filter];
    }
    var sheets = document.styleSheets;
    for (var i = 0; i < sheets.length; i++) {
        var rules;
        // try...catch because browser may not able to enumerate rules for cross-domain stylesheets
        try {
            rules = sheets[i].rules || sheets[i].cssRules;
        } catch(e) {
            console.warn("Can't read the css rules of: " + sheets[i].href, e);
            continue;
        }
        if (rules) {
            for (var r = 0; r < rules.length; r++) {
                var selectorText = rules[r].selectorText;
                if (selectorText) {
                    selectorText = selectorText.split(/\s*,\s*/);
                    var data = null;
                    for (var s = 0; s < selectorText.length; s++) {
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
var computeFonts = _.once(function () {
    _.each(fontIcons, function (data) {
        data.cssData = getCssSelectors(data.parser);
        data.alias = [];
        data.icons = _.map(data.cssData, function (css) {
            data.alias.push.apply(data.alias, css[3]);
            return css[2];
        });
    });
});

/**
 * FontIconsDialog widget. Lets users change a font awesome, support all
 * font awesome loaded in the css files.
 */
var fontIconsDialog = Widget.extend({
    template: 'web_editor.dialog.font-icons',
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],
    events : _.extend({}, Dialog.prototype.events, {
        'click .font-icons-icon': function (e) {
            e.preventDefault();
            e.stopPropagation();

            this.$('#fa-icon').val(e.target.getAttribute('data-id'));
            this.$(".font-icons-icon").removeClass("o_selected");
            $(e.target).addClass("o_selected");
        },
        'dblclick .font-icons-icon': function () {
            this.getParent().save();
        },
        'keydown.dismiss.bs.modal': function () {},
    }),

    init: function (parent, media) {
        this._super.apply(this, arguments);
        this.parent = parent;
        this.media = media;
        computeFonts();
    },
    start: function () {
        return this._super.apply(this, arguments).then(this.proxy('load_data'));
    },
    renderElement: function () { // extract list of font (like awesome) from the cheatsheet.
        this.iconsParser = fontIcons;
        this.icons = _.flatten(_.map(fontIcons, function (data) { // TODO maybe useless now
            return data.icons;
        }));
        this.alias = _.flatten(_.map(fontIcons, function (data) {
            return data.alias;
        }));
        this._super.apply(this, arguments);
    },
    search: function (needle) {
        var iconsParser = this.iconsParser;
        if (needle) {
            iconsParser = [];
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

        return this.media;
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
            switch (cls) {
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
                    this.$(".font-icons-icon").removeClass("o_selected").filter("[data-alias*=',"+cls+",']").addClass("o_selected");
                    if (this.alias.indexOf(cls) !== -1) {
                        this.$('#fa-icon').val(cls);
                    }
            }
        }
    },
    /**
     * Serializes the dialog to an array of FontAwesome classes. Includes the base ``fa``.
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
        if (!this.media) {
            return;
        }
        this.media.className = this.media.className.replace(/(^|\s)(fa(\s|$)|fa-[^\s]*)/g, ' ');
    },
});

/**
 * VideoDialog widget. Let users change a video, support all summernote
 * video, and embed iframe.
 */
var VideoDialog = Widget.extend({
    template: 'web_editor.dialog.video',
    xmlDependencies: ['/web_editor/static/src/xml/editor.xml'],
    events : {
        'change .o_video_dialog_options input': '_onUpdateVideoOption',
        'input textarea#o_video_text': '_onVideoCodeInput',
        'change textarea#o_video_text': '_onVideoCodeChange',
    },

    /**
     * @constructor
     */
    init: function (parent, media) {
        this._super.apply(this, arguments);
        this.parent = parent;
        this.media = media;
        this._onVideoCodeInput = _.debounce(this._onVideoCodeInput, 1000);
    },
    /**
     * @override
     */
    start: function () {
        this.$preview = this.$('.preview-container').detach();
        this.$content = this.$('.o_video_dialog_iframe');

        var $media = $(this.media);
        if ($media.hasClass('media_iframe_video')) {
            var src = $media.data('oe-expression') || $media.data('src') || '';
            this.$('textarea#o_video_text').val(src);

            this.$('input#o_video_autoplay').prop('checked', src.indexOf('autoplay=1') >= 0);
            this.$('input#o_video_hide_controls').prop('checked', src.indexOf('controls=0') >= 0);
            this.$('input#o_video_loop').prop('checked', src.indexOf('loop=1') >= 0);
            this.$('input#o_video_hide_fullscreen').prop('checked', src.indexOf('fs=0') >= 0);
            this.$('input#o_video_hide_yt_logo').prop('checked', src.indexOf('modestbranding=1') >= 0);
            this.$('input#o_video_hide_dm_logo').prop('checked', src.indexOf('ui-logo=0') >= 0);
            this.$('input#o_video_hide_dm_share').prop('checked', src.indexOf('sharing-enable=0') >= 0);

            this._updateVideo();
        }

        return this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    save: function () {
        this._updateVideo();

        if (this.$('.o_video_dialog_iframe').is('iframe')) {
            var $content = $(
                '<div class="media_iframe_video" data-oe-expression="' + this.$content.attr('src') + '">'+
                    '<div class="css_editable_mode_display">&nbsp;</div>'+
                    '<div class="media_iframe_video_size" contenteditable="false">&nbsp;</div>'+
                    '<iframe src="' + this.$content.attr('src') + '" frameborder="0" contenteditable="false"></iframe>'+
                '</div>'
            );
            $(this.media).replaceWith($content);
            this.media = $content[0];
            return this.media;
        }
    },
    /**
     * @override
     */
    clear: function () {
        if (!this.media) {
            return;
        }
        if (this.media.dataset.src) {
            try {
                delete this.media.dataset.src;
            } catch (e) {
                this.media.dataset.src = undefined;
            }
        }
        this.media.className = this.media.className.replace(/(^|\s)media_iframe_video(\s|$)/g, ' ');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Creates a video node according to the given URL and options. If not
     * possible, returns an error code.
     *
     * @private
     * @param {string} url
     * @param {Object} options
     * @returns {Object}
     *          $video -> the created video jQuery node
     *          type -> the type of the created video
     *          errorCode -> if defined, either '0' for invalid URL or '1' for
     *              unsupported video provider
     */
    _createVideoNode: function (url, options) {
        options = options || {};

        // Video url patterns(youtube, instagram, vimeo, dailymotion, youku, ...)
        var ytRegExp = /^(?:(?:https?:)?\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))((\w|-){11})(?:\S+)?$/;
        var ytMatch = url.match(ytRegExp);

        var insRegExp = /(.*)instagram.com\/p\/(.[a-zA-Z0-9]*)/;
        var insMatch = url.match(insRegExp);

        var vinRegExp = /\/\/vine.co\/v\/(.[a-zA-Z0-9]*)/;
        var vinMatch = url.match(vinRegExp);

        var vimRegExp = /\/\/(player.)?vimeo.com\/([a-z]*\/)*([0-9]{6,11})[?]?.*/;
        var vimMatch = url.match(vimRegExp);

        var dmRegExp = /.+dailymotion.com\/(video|hub|embed)\/([^_]+)[^#]*(#video=([^_&]+))?/;
        var dmMatch = url.match(dmRegExp);

        var ykuRegExp = /(.*).youku\.com\/(v_show\/id_|embed\/)(.+)/;
        var ykuMatch = url.match(ykuRegExp);

        var $video = $('<iframe>').width(1280).height(720).attr('frameborder', 0).addClass('o_video_dialog_iframe');
        var videoType = 'yt';

        if (!/^(http:\/\/|https:\/\/|\/\/)[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?$/i.test(url)){
            return {errorCode: 0};
        }

        var autoplay = options.autoplay ? '?autoplay=1' : '?autoplay=0';

        if (ytMatch && ytMatch[1].length === 11) {
            $video.attr('src', '//www.youtube.com/embed/' + ytMatch[1] + autoplay);
        } else if (insMatch && insMatch[2].length) {
            $video.attr('src', '//www.instagram.com/p/' + insMatch[2] + '/embed/');
            videoType = 'ins';
        } else if (vinMatch && vinMatch[0].length) {
            $video.attr('src', vinMatch[0] + '/embed/simple');
            videoType = 'vin';
        } else if (vimMatch && vimMatch[3].length) {
            $video.attr('src', '//player.vimeo.com/video/' + vimMatch[3] + autoplay);
            videoType = 'vim';
        } else if (dmMatch && dmMatch[2].length) {
            var just_id = dmMatch[2].replace('video/','');
            $video.attr('src', '//www.dailymotion.com/embed/video/' + just_id + autoplay);
            videoType = 'dm';
        } else if (ykuMatch && ykuMatch[3].length) {
            var yku_id = ykuMatch[3].indexOf('.html?') >= 0 ? ykuMatch[3].substring(0, ykuMatch[3].indexOf('.html?')) : ykuMatch[3];
            $video.attr('src', '//player.youku.com/embed/' + yku_id);
            videoType = 'yku';
        } else {
            return {errorCode: 1};
        }

        if (ytMatch) {
            $video.attr('src', $video.attr('src') + '&rel=0');
        }
        if (options.loop && (ytMatch || vimMatch)) {
            $video.attr('src', $video.attr('src') + '&loop=1');
        }
        if (options.hide_controls && (ytMatch || dmMatch)) {
            $video.attr('src', $video.attr('src') + '&controls=0');
        }
        if (options.hide_fullscreen && ytMatch) {
            $video.attr('src', $video.attr('src') + '&fs=0');
        }
        if (options.hide_yt_logo && ytMatch) {
            $video.attr('src', $video.attr('src') + '&modestbranding=1');
        }
        if (options.hide_dm_logo && dmMatch) {
            $video.attr('src', $video.attr('src') + '&ui-logo=0');
        }
        if (options.hide_dm_share && dmMatch) {
            $video.attr('src', $video.attr('src') + '&sharing-enable=0');
        }

        return {$video: $video, type: videoType};
    },
    /**
     * Updates the video preview according to video code and enabled options.
     *
     * @private
     */
    _updateVideo: function () {
        // Reset the feedback
        this.$content.empty();
        this.$('#o_video_form_group').removeClass('has-error has-success');
        this.$('.o_video_dialog_options li').addClass('hidden');

        // Check video code
        var $textarea = this.$('textarea#o_video_text');
        var code = $textarea.val().trim();
        if (!code) {
            return;
        }

        // Detect if we have an embed code rather than an URL
        var embedMatch = code.match(/(src|href)=["']?([^"']+)?/);
        if (embedMatch && embedMatch[2].length > 0 && embedMatch[2].indexOf('instagram')){
            embedMatch[1] = embedMatch[2]; // Instagram embed code is different
        }
        var url = embedMatch ? embedMatch[1] : code;

        var query = this._createVideoNode(url, {
            autoplay: this.$('input#o_video_autoplay').is(':checked'),
            hide_controls: this.$('input#o_video_hide_controls').is(':checked'),
            loop: this.$('input#o_video_loop').is(':checked'),
            hide_fullscreen: this.$('input#o_video_hide_fullscreen').is(':checked'),
            hide_yt_logo: this.$('input#o_video_hide_yt_logo').is(':checked'),
            hide_dm_logo: this.$('input#o_video_hide_dm_logo').is(':checked'),
            hide_dm_share: this.$('input#o_video_hide_dm_share').is(':checked'),
        });

        var $opt_box = this.$('.o_video_dialog_options');

        // Show / Hide preview elements
        this.$el.find('.o_video_dialog_preview_text, .media_iframe_video_size').add($opt_box).toggleClass('hidden', !query.$video);
        // Toggle validation classes
        this.$el.find('#o_video_form_group').toggleClass('has-error', !query.$video).toggleClass('has-success', !!query.$video);

        // Individually show / hide options base on the video provider
        $opt_box.find('li.o_' + query.type + '_option').removeClass('hidden');

        // Hide the entire options box if no options are available
        $opt_box.toggleClass('hidden', $opt_box.find('li:not(.hidden)').length === 0);

        if (query.type === 'yt') {
            // Youtube only: If 'hide controls' is checked, hide 'fullscreen'
            // and 'youtube logo' options too
            this.$('input#o_video_hide_fullscreen, input#o_video_hide_yt_logo').closest('li').toggleClass('hidden', this.$('input#o_video_hide_controls').is(':checked'));
        }

        var $content = query.$video;
        if (!$content) {
            switch (query.errorCode) {
                case 0:
                    $content = $('<div/>', {
                        class: 'alert alert-danger o_video_dialog_iframe',
                        text: _t("The provided url is not valid"),
                    });
                    break;
                case 1:
                    $content = $('<div/>', {
                        class: 'alert alert-warning o_video_dialog_iframe',
                        text: _t("The provided url does not reference any supported video"),
                    });
                    break;
            }
        }
        this.$content.replaceWith($content);
        this.$content = $content;
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Called when a video option changes -> Updates the video preview.
     *
     * @private
     */
    _onUpdateVideoOption: function () {
        this._updateVideo();
    },
    /**
     * Called when the video code (URL / Iframe) change is confirmed -> Updates
     * the video preview immediately.
     *
     * @private
     */
    _onVideoCodeChange: function () {
        this._updateVideo();
    },
    /**
     * Called when the video code (URL / Iframe) changes -> Updates the video
     * preview (note: this function is automatically debounced).
     *
     * @private
     */
    _onVideoCodeInput: function () {
        this._updateVideo();
    },
});

/**
 * MediaDialog widget. Lets users change a media, including uploading a
 * new image, font awsome or video and can change a media into an other
 * media
 *
 * options: select_images: allow the selection of more of one image
 */
var MediaDialog = Dialog.extend({
    template: 'web_editor.dialog.media',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/editor.xml']
    ),
    events : _.extend({}, Dialog.prototype.events, {
        'input input#icon-search': 'search',
    }),
    init: function (parent, options, $editable, media) {
        this._super(parent, _.extend({}, {
            title: _t("Select a Media"),
        }, options));
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

        this.$modal.addClass('note-image-dialog');
        this.$modal.find('.modal-dialog').addClass('o_select_media_dialog');

        this.only_images = this.options.only_images || this.options.select_images || (this.media && ($(this.media).parent().data("oe-field") === "image" || $(this.media).parent().data("oe-type") === "image"));
        if (this.only_images) {
            this.$('[href="#editor-media-document"], [href="#editor-media-video"], [href="#editor-media-icon"]').addClass('hidden');
        }

        this.opened((function () {
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
        }).bind(this));

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

        this.$('a[data-toggle="tab"]').on('shown.bs.tab', function (event) {
            if ($(event.target).is('[href="#editor-media-image"]')) {
                self.active = self.imageDialog;
                self.$('li.search, li.previous, li.next').removeClass("hidden");
            } else if ($(event.target).is('[href="#editor-media-document"]')) {
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

        return this._super.apply(this, arguments);
    },
    save: function () {
        var self = this;
        var args = arguments;
        var _super = this._super;
        if (this.options.select_images) {
            return $.when(this.active.save()).then(function (data) {
                self.final_data = data;
                return _super.apply(self, args);
            });
        }
        if (this.rte) {
            this.range.select();
            this.rte.historyRecordUndo(this.media);
        }

        if (this.media) {
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

        return $.when(this.active.save()).then(function () {
            if (self.active.add_class) {
                $(self.active.media).addClass(self.active.add_class);
            }
            var media = self.active.media;

            self.final_data = [media, self.old_media];
            $(document.body).trigger("media-saved", self.final_data);
            $(self.old_media).trigger("save", self.final_data);
            $(self.final_data).trigger('input');

            // Update editor bar after image edition (in case the image change to icon or other)
            _.defer(function () {
                if (!media.parentNode) return;
                range.createFromNode(media).select();
                click_event(media, "mousedown");
                click_event(media, "mouseup");
            });
            return _super.apply(self, args);
        });
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
 * The Link Dialog allows to customize link content and style.
 */
var LinkDialog = Dialog.extend({
    template: 'web_editor.dialog.link',
    xmlDependencies: Dialog.prototype.xmlDependencies.concat(
        ['/web_editor/static/src/xml/editor.xml']
    ),
    events: _.extend({}, Dialog.prototype.events, {
        'change :input.url-source': 'changed',
        'keyup :input.url': 'onkeyup',
        'keyup :input': 'preview',
        'click button.remove': 'remove_link',
        'change input#o_link_dialog_label_input': function (e) {
            this.text = $(e.target).val();
        },
        'change .link-style': function (e) {
            this.preview();
        },
    }),
    init: function (parent, options, editable, linkInfo) {
        this._super(parent, _.extend({}, {
            title: _t("Link to")
        }, options || {}));
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
        this.$('#o_link_dialog_label_input').focus();
        return this._super.apply(this, arguments);
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
        var label = this.$('#o_link_dialog_label_input').val() || val;

        if (label && this.data.images) {
            for (var i=0; i<this.data.images.length; i++) {
                label = label.replace(/</, "&lt;").replace(/>/, "&gt;").replace(/\[IMG\]/, this.data.images[i].outerHTML);
            }
        }

        if (!test && $e.prop('required') && (!val || !$e[0].checkValidity())) {
            // FIXME: error message
            $e.closest('.form-group').addClass('has-error');
            $e.focus();
            def.reject();
        }

        var style = this.$("input[name='link-style-type']:checked").val() || '';
        var size = this.$("select.link-style").val() || '';
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
        return this.get_data().then(function (url, new_window, label, classes) {
            self.data.url = url;
            self.data.isNewWindow = new_window;
            self.data.text = label;
            self.data.className = classes.replace(/\s+/gi, ' ').replace(/^\s+|\s+$/gi, '');
                if (classes.replace(/(^|[ ])(btn-default|btn-success|btn-primary|btn-info|btn-warning|btn-danger)([ ]|$)/gi, ' ')) {
                    self.data.style = {'background-color': '', 'color': ''};
                }
            self.final_data = self.data;
        }).then(_super);
    },
    bind_data: function () {
        var href = this.data.url;
        var new_window = this.data.isNewWindow;
        var text = this.data.text;
        var classes = this.data.iniClassName;

        this.$('input#o_link_dialog_label_input').val(text);
        this.$('input.window-new').prop('checked', new_window);
        this.$('input.link-style').prop('checked', false).first().prop("checked", true);

        if (classes) {
            this.$('input.link-style, select.link-style > option').each(function () {
                var $option = $(this);
                if ($option.val() && classes.indexOf($option.val()) >= 0) {
                    if ($option.is("input")) {
                        $option.prop("checked", true);
                    } else {
                        $option.parent().val($option.val());
                    }
                }
            });
        }

        if (href) {
            var match = /mailto:(.+)/.exec(href);
            if (match) {
                this.$('input.email-address').val(match = /mailto:(.+)/.exec(href) ? match[1] : '');
            } else {
                this.$('input.url').val(href);
                this.$('input.window-new').closest("div").show();
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
        var is_link = $e.val().indexOf("@") === -1;
        this.$('input.window-new').closest("div").toggle(is_link);
        this.preview();
    },
    preview: function () {
        var $preview = this.$("#link-preview");
        this.get_data(true).then(function (url, new_window, label, classes) {
            $preview.attr("target", new_window ? '_blank' : "")
                .attr("href", url && url.length ? url : "#")
                .html((label && label.length ? label : url))
                .attr("class", classes.replace(/pull-\w+/, '') + " o_btn_preview");
        });
    }
});

return {
    Dialog: Dialog,
    alt: alt,
    MediaDialog: MediaDialog,
    LinkDialog: LinkDialog,
    getCssSelectors: getCssSelectors,
    fontIcons: fontIcons,
    computeFonts: computeFonts,
    click_event: click_event,
    fontIconsDialog: fontIconsDialog,
    ImageDialog: ImageDialog,
    VideoDialog: VideoDialog,
};
});
