openerp.website = function(instance) {

instance.web.ActionManager.include({
    // Temporary fix until un-webclientization of the editorbar
    ir_actions_client: function (action) {
        if (instance.web.client_actions.get_object(action.tag)) {
            return this._super.apply(this, arguments);
        } else {
            console.warn("Action '%s' not found in registry", action.tag);
            return $.when();
        }
    }
});

var _lt = instance.web._lt;
var QWeb = instance.web.qweb;
instance.website.EditorBar = instance.web.Widget.extend({
    template: 'Website.EditorBar',
    events: {
        'click button[data-action=edit]': 'edit',
        'click button[data-action=save]': 'save',
        'click button[data-action=cancel]': 'cancel',
        'click button[data-action=snippet]': 'snippet',
    },
    container: 'body',
    init: function () {
        this._super.apply(this, arguments);
        this.saving_mutex = new $.Mutex();
    },
    start: function() {
        var self = this;

        this.$('button[data-action]').prop('disabled', true)
            .parent().hide();
        this.$buttons = {
            edit: this.$('button[data-action=edit]'),
            save: this.$('button[data-action=save]'),
            cancel: this.$('button[data-action=cancel]'),
            snippet: this.$('button[data-action=snippet]'),
        };
        this.$buttons.edit.prop('disabled', false).parent().show();

        self.snippet_start();

        this.rte = new instance.website.RTE(this);
        this.rte.on('change', this, this.proxy('rte_changed'));

        return $.when(
            this._super.apply(this, arguments),
            this.rte.insertBefore(this.$buttons.snippet.parent())
        );
    },
    edit: function () {
        this.$buttons.edit.prop('disabled', true).parent().hide();
        this.$buttons.cancel.add(this.$buttons.snippet)
            //.prop('disabled', false)
            .add(this.$buttons.save)
            .prop('disabled', false)
            .parent().show();
        // TODO: span edition changing edition state (save button)
        var $editables = $('[data-oe-model]')
                .filter('div, p, li, section, header, footer')
                .filter('[data-oe-xpath]')
                .not('[data-oe-type]')
                // FIXME: propagation should make "meta" blocks non-editable in the first place...
                .not('.oe_snippet_editor')
                .prop('contentEditable', true)
                .addClass('oe_editable');
        this.rte.start_edition($editables);
    },
    rte_changed: function () {
        this.$buttons.save.prop('disabled', false);
    },
    save: function () {
        var self = this;

        var defs = _(CKEDITOR.instances).chain()
            .filter(function (editor) { return editor.checkDirty(); })
            .map(function (editor) {
                console.log('Saving', editor);
                // TODO: Add a queue with concurrency limit in webclient
                // https://github.com/medikoo/deferred/blob/master/lib/ext/function/gate.js
                return self.saving_mutex.exec(function () {
                    var $el = $(editor.element.$);
                    return self.saveEditor(editor)
                        .fail(function () {
                            var data = $el.data();
                            console.error(_.str.sprintf('Could not save %s(%d).%s', data.oeModel, data.oeId, data.oeField));
                        });
                });
            }).value();
        return $.when.apply(null, defs).then(function () {
            window.location.reload();
        });
    },
    /**
     * Saves an RTE content, which always corresponds to a view section (?).
     *
     *
     */
    saveEditor: function (editor) {
        var element = editor.element;
        var data = editor.getData();
        return new instance.web.Model('ir.ui.view').call('save', {
            res_id: element.data('oe-id'),
            xpath: element.data('oe-xpath'),
            value: data,
        });
    },
    cancel: function () {
        window.location.reload();
    },
    setup_droppable: function () {
        var self = this;
        $('.oe_snippet_drop').remove();
        var droppable = '<div class="oe_snippet_drop"></div>';
        var $zone = $(':not(.oe_snippet) > .container');
        $zone.after(droppable);//.after(droppable);

        $(".oe_snippet_drop").droppable({
            hoverClass: 'oe_accepting',
            drop: function( event, ui ) {
                console.log(event, ui, "DROP");

                $(event.target).replaceWith($(ui.draggable).html());
                $('.oe_selected').remove();
                $('.oe_snippet_drop').remove();
            }
        });
    },
    snippet_start: function () {
        var self = this;
        $('.oe_snippet').draggable().click(function(ev) {
            self.setup_droppable();
            $(".oe_snippet_drop").show();
            $('.oe_selected').removeClass('oe_selected');
            $(ev.currentTarget).addClass('oe_selected');
        });

    },
    snippet: function (ev) {
        $('.oe_snippet_editor').toggle();
    },
});

instance.website.RTE = instance.web.Widget.extend({
    tagName: 'li',
    id: 'oe_rte_toolbar',
    className: 'oe_right oe_rte_toolbar',
    // editor.ui.items -> possible commands &al
    // editor.applyStyle(new CKEDITOR.style({element: "span",styles: {color: "#(color)"},overrides: [{element: "font",attributes: {color: null}}]}, {color: '#ff0000'}));

    start_edition: function ($elements) {
        var self = this;
        this.snippet_carousel();
        $elements
            .each(function () {
                var $this = $(this);
                var editor = CKEDITOR.inline(this, self._config());
                editor.on('change', function () {
                    self.trigger('change', this, null);
                });
            });
    },

    _current_editor: function () {
        return CKEDITOR.currentInstance;
    },
    _config: function () {
        var removed_plugins = [
                // remove custom context menu
                'contextmenu,tabletools,liststyle',
                // magicline captures mousein/mouseout => draggable does not work
                'magicline'
        ];
        return {
            removePlugins: removed_plugins.join(','),
            uiColor: '',
            // Ensure no config file is loaded
            customConfig: '',
            // Disable ACF
            allowedContent: true,
            // Don't insert paragraphs around content in e.g. <li>
            autoParagraph: false,
            filebrowserImageUploadUrl: "/website/attach",
            // Support for sharedSpaces in 4.x
            extraPlugins: 'sharedspace,oeref',
            // Place toolbar in controlled location
            sharedSpaces: { top: 'oe_rte_toolbar' },
            toolbar: [
                {name: 'items', items: [
                    "Bold", "Italic", "Underline", "Strike", "Subscript",
                    "Superscript", "TextColor", "BGColor", "RemoveFormat",
                    "Link", "Unlink", "Blockquote", "BulletedList",
                    "NumberedList", "Image", "Indent", "Outdent",
                    "JustifyLeft", "JustifyCenter", "JustifyRight",
                    "JustifyBlock", "Table", "Font", "FontSize", "Format",
                    "Styles"
                ]}
            ],
            // styles dropdown in toolbar
            stylesSet: [
                // emphasis
                {name: "Muted", element: 'span', attributes: {'class': 'text-muted'}},
                {name: "Primary", element: 'span', attributes: {'class': 'text-primary'}},
                {name: "Warning", element: 'span', attributes: {'class': 'text-warning'}},
                {name: "Danger", element: 'span', attributes: {'class': 'text-danger'}},
                {name: "Success", element: 'span', attributes: {'class': 'text-success'}},
                {name: "Info", element: 'span', attributes: {'class': 'text-info'}}
            ],
        };
    },
    // TODO clean
    snippet_carousel: function () {
        var self = this;
        $('.carousel .js_carousel_options .label').on('click', function (e) {
            e.preventDefault();
            var $button = $(e.currentTarget)
            var $c = $button.parents(".carousel:first");

            if($button.hasClass("js_add")) {
                var cycle = $c.find(".carousel-inner .item").size();
                $c.find(".carousel-inner").append(QWeb.render("Website.Snipped.carousel"));
                $c.carousel(cycle);
            }
            else {
                var cycle = $c.find(".carousel-inner .item.active").remove();
                $c.find(".carousel-inner .item:first").addClass("active");
                $c.carousel(0);
                self.trigger('change', self, null);
            }
        });
        $('.carousel .js_carousel_options').show();
    }
});

$(function(){

    function make_static(){
        $('.oe_snippet_demo').removeClass('oe_new');
        $('.oe_page *').off('mouseover mouseleave');
        $('.oe_page .oe_selected').removeClass('oe_selected');
    }

    var selected_snippet = null;
    function snippet_click(event){
        if(selected_snippet){
            selected_snippet.removeClass('oe_selected');
            if(selected_snippet[0] === $(this)[0]){
                selected_snippet = null;
                event.preventDefault();
                make_static();
                return;
            }
        }
        $(this).addClass('oe_selected');
        selected_snippet = $(this);
        make_editable();
        event.preventDefault();
    }
    //$('.oe_snippet').click(snippet_click);

    var hover_element = null;

    function make_editable( constraint_after, constraint_inside ){
        if(selected_snippet && selected_snippet.hasClass('oe_new')){
            $('.oe_snippet_demo').addClass('oe_new');
        }else{
            $('.oe_snippet_demo').removeClass('oe_new');
        }
    
        $('.oe_page *').off('mouseover');
        $('.oe_page *').off('mouseleave');
        $('.oe_page *').mouseover(function(event){
            console.log('hover:',this);
            if(hover_element){
                hover_element.removeClass('oe_selected');
                hover_element.off('click');
            }
            $(this).addClass('oe_selected');
            $(this).click(append_snippet);
            hover_element = $(this);
            event.stopPropagation();
        });
        $('.oe_page *').mouseleave(function(){
            if(hover_element && $(this) === hover_element){
                hover_element = null;
                $(this).removeClass('oe_selected');
            }
        });
    }

    function append_snippet(event){
        console.log('click',this,event.button);
        if(event.button === 0){
            if(selected_snippet){
                if(selected_snippet.hasClass('oe_new')){
                    var new_snippet = $("<div class='oe_snippet'></div>");
                    new_snippet.append($(this).clone());
                    new_snippet.click(snippet_click);
                    $('.oe_snippet.oe_selected').before(new_snippet);
                }else{
                    $(this).after($('.oe_snippet.oe_selected').contents().clone());
                }
                selected_snippet.removeClass('oe_selected');
                selected_snippet = null;
                make_static();
            }
        }else if(event.button === 1){
            $(this).remove();
        }
        event.preventDefault();
    }
});

instance.web.ActionRedirect = function(parent, action) {
    var url = $.deparam(window.location.href).url;
    if (url) {
        window.location.href = url;
    }
};
instance.web.client_actions.add("redirect", "instance.web.ActionRedirect");

instance.web.GoToWebsite = function(parent, action) {
    window.location.href = window.location.href.replace(/[?#].*/, '').replace(/\/admin[\/]?$/, '');
};
instance.web.client_actions.add("website.gotowebsite", "instance.web.GoToWebsite");

if (!window.CKEDITOR) { return; }

CKEDITOR.plugins.add('oeref', {
    requires: 'widget',

    init: function (editor) {
        editor.widgets.add('oeref', {
            inline: true,
            // dialog: 'oeref',
            allowedContent: '[data-oe-type]',
            editables: { text: '*' },

            init: function () {
                var element = this.element;
                this.setData({
                    model: element.data('oe-model'),
                    id: parseInt(element.data('oe-id'), 10),
                    field: element.data('oe-field'),
                });
            },
            data: function () {
                this.element.data('oe-model', this.data.model);
                this.element.data('oe-id', this.data.id);
                this.element.data('oe-field', this.data.field);
            },
            upcast: function (el) {
                return el.attributes['data-oe-type'];
            },
        });
    }
});
};
