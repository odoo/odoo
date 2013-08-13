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
    customize_setup: function() {
        var self = this;
        var view_name = $('html').data('view-xmlid');
        var menu = $('#customize-menu');
        this.$('#customize-menu-button').click(function(event) {
            menu.empty();
            self.rpc('/website/customize_template_get', { 'xml_id': view_name }).then(
                function(result) {
                    _.each(result, function (item) {
                        if (item.header) {
                            menu.append('<li class="nav-header">' + item.name + '</li>');
                        } else {
                            menu.append(_.str.sprintf('<li><a href="#" data-view-id="%s"><strong class="icon-check%s"></strong> %s</a></li>',
                                item.id, item.active ? '' : '-empty', item.name));
                        }
                    });
                }
            );
        });
        menu.on('click', 'a', function (event) {
            var view_id = $(event.target).data('view-id');
            self.rpc('/website/customize_template_toggle', {
                'view_id': view_id
            }).then( function(result) {
                window.location.reload();
            });
        });
    },
    start: function() {
        var self = this;

        this.$('#website-top-edit').hide();
        this.$('#website-top-view').show();

        $('.dropdown-toggle').dropdown();
        this.customize_setup();

        this.$buttons = {
            edit: this.$('button[data-action=edit]'),
            save: this.$('button[data-action=save]'),
            cancel: this.$('button[data-action=cancel]'),
            snippet: this.$('button[data-action=snippet]'),
        };

        self.snippet_start();

        this.rte = new instance.website.RTE(this);
        this.rte.on('change', this, this.proxy('rte_changed'));

        return $.when(
            this._super.apply(this, arguments),
            this.rte.insertBefore(this.$buttons.snippet.parent())
        );
    },
    edit: function () {
        this.$buttons.edit.prop('disabled', true);
        this.$('#website-top-view').hide();
        this.$('#website-top-edit').show();

        // this.$buttons.cancel.add(this.$buttons.snippet).prop('disabled', false)
        //     .add(this.$buttons.save)
        //     .parent().show();
        //
        // TODO: span edition changing edition state (save button)
        var $editables = $('[data-oe-model]')
                .not('link, script')
                // FIXME: propagation should make "meta" blocks non-editable in the first place...
                .not('.oe_snippet_editor')
                .prop('contentEditable', true)
                .addClass('oe_editable');
        var $rte_ables = $editables.filter('div, p, li, section, header, footer').not('[data-oe-type]');
        var $raw_editables = $editables.not($rte_ables);

        // temporary fix until we fix ckeditor
        $raw_editables.each(function () {
            $(this).parents().add($(this).find('*')).on('click', function(ev) {
                ev.preventDefault();
                ev.stopPropagation();
            });
        });

        this.rte.start_edition($rte_ables);
        $raw_editables.on('keydown keypress cut paste', function (e) {
            var $target = $(e.target);
            if ($target.hasClass('oe_dirty')) {
                return;
            }

            $target.addClass('oe_dirty');
            this.$buttons.save.prop('disabled', false);
        }.bind(this));
    },
    rte_changed: function () {
        this.$buttons.save.prop('disabled', false);
    },
    save: function () {
        var self = this;
        var defs = [];
        $('.oe_dirty').each(function (i, v) {
            var $el = $(this);
            // TODO: Add a queue with concurrency limit in webclient
            // https://github.com/medikoo/deferred/blob/master/lib/ext/function/gate.js
            var def = self.saving_mutex.exec(function () {
                return self.saveElement($el).then(function () {
                    $el.removeClass('oe_dirty');
                }).fail(function () {
                    var data = $el.data();
                    console.error(_.str.sprintf('Could not save %s#%d#%s', data.oeModel, data.oeId, data.oeField));
                });
            });
            defs.push(def);
        });
        return $.when.apply(null, defs).then(function () {
            window.location.reload();
        });
    },
    saveElement: function ($el) {
        var data = $el.data();
        var html = $el.html();
        var xpath = data.oeXpath;
        if (xpath) {
            var $w = $el.clone();
            $w.removeClass('oe_dirty');
            _.each(['model', 'id', 'field', 'xpath'], function(d) {$w.removeAttr('data-oe-' + d);});
            $w
                .removeClass('oe_editable')
                .prop('contentEditable', false);
            html = $w.wrap('<div>').parent().html();
        }
        return (new instance.web.DataSet(this, 'ir.ui.view')).call('save', [data.oeModel, data.oeId, data.oeField, html, xpath]);
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
            .not('span, [data-oe-type]')
            .each(function () {
                var $this = $(this);
                CKEDITOR.inline(this, self._config()).on('change', function () {
                    $this.addClass('oe_dirty');
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
            extraPlugins: 'sharedspace',
            // Place toolbar in controlled location
            sharedSpaces: { top: 'oe_rte_toolbar' },
            toolbar: [
                {name: 'basicstyles', items: [
                    "Bold", "Italic", "Underline", "Strike", "Subscript",
                    "Superscript", "TextColor", "BGColor", "RemoveFormat"
                ]},{
                name: 'span', items: [
                    "Link", "Unlink", "Blockquote", "BulletedList",
                    "NumberedList", "Indent", "Outdent",
                ]},{
                name: 'justify', items: [
                    "JustifyLeft", "JustifyCenter", "JustifyRight", "JustifyBlock"
                ]},{
                name: 'special', items: [
                    "Image", "Table"
                ]},{
                name: 'styles', items: [
                    "Format", "Styles"
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
            var $button = $(e.currentTarget);
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

    function customier_option_get(event){


        event.preventDefault();
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

};
