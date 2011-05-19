openerp.base.m2o = function(openerp){

    openerp.base.m2o = openerp.base.Controller.extend({
        init: function(view_manager, element_id, model, dataset, session){
            this._super(element_id, model, dataset, session);

            this.view_manager = view_manager;
            this.session = session;
            this.element = element_id.find('input');
            this.button = element_id.find('span');
            this.dataset = dataset;
            this.cache = {};
            var lastXhr;
            this.$input;
            this.relation = model;
            this.result_ids = [];
            this.create_option = jQuery('#'+this.element.attr('name')+ '_open');
            if (this.create_option) {
                var defaults = [
                    {'text': 'Go to..', 'action': "call_Actions()"},
                    {'text': 'Choose..', 'action': "call_Actions()"}
                ]
                jQuery(this.create_option).click(jQuery.proxy(function(evt){
                    on_context_menu(evt, this.element, defaults);
                }, this));
            }
            var self = this;

            this.$input = this.element.autocomplete ({
                source: function(request, response){
                    self.getSearch_Result(request, response);
                    return;
                },
                select: function(event, ui){
                    self.getSelected_Result(event, ui);
                },
                minLength: 0,
                focus: function(event, ui) {
                    self.gotFocus(event, ui);
                }
            });

            this.button.button({
                icons: {
                    primary: "ui-icon-triangle-1-s"},
                    text: false
            })
            .click(function() {
                // close if already visible
                if (self.$input.autocomplete("widget").is(":visible")) {
                    self.$input.autocomplete( "close" );
                    return;
                }
                $(this).blur();
                self.$input.autocomplete("search", "" );
                self.$input.focus();
            });
        },

        getSearch_Result: function(request, response) {
            var search_val = request.term;
            if (search_val in this.cache) {
                response(this.cache[search_val]);
                return;
            }
            var self = this;
            //pass request to server
            lastXhr = this.dataset.name_search(search_val, function(obj, status, xhr){
                var result = obj.result;
                var values = [];

                $.each(result, function(i, val){
                    values.push({
                        value: val[1],
                        id: val[0],
                        orig_val: val[1]
                    });
                    self.result_ids.push(result[i][0]);
                });

                if (values.length > 7) {
                    values = values.slice(0, 7);
                }
                values.push({'value': 'More...', id: 'more', orig_val:''},
                            {'value': 'Create..'+search_val, id: 'create', orig_val: ''});
                self.cache[search_val] = values;
                response(values);
            });
        },

        getSelected_Result: function(event, ui) {
            ui.item.value = ui.item.orig_val? ui.item.orig_val : this.element.data( "autocomplete" ).term;
            if (ui.item.id == 'more') {
                this.dataset.ids = this.result_ids;
                this.dataset.count = this.dataset.ids.length;
                this.dataset.domain = this.result_ids.length ? [["id", "in", this.dataset.ids]] : [];
                this.element.val('');
                var pop = new openerp.base.form.Many2XSelectPopup(null, this.session);
                pop.select_element(this.relation, this.dataset);
                return;
            }

            if (ui.item.id == 'create') {
                this.openRecords(event, ui);
            }
            this.element.attr('m2o_id', ui.item.id);
        },

        gotFocus: function(event, ui) {
            if (ui.item.id == ('create')) {
                return true;
            }
            ui.item.value = this.element.data("autocomplete").term.length ?
                this.element.val() + '[' + ui.item.orig_val.substring(this.element.data("autocomplete").term.length) + ']' : this.lastSearch;
        },

        openRecords: function(event, ui) {
            var val = this.element.val();
            var self = this;
                this.dataset.create({'name': ui.item.value},
                    function(r){}, function(r){
                        var element_id = _.uniqueId("act_window_dialog");
                        var dialog = jQuery('<div>',
                                                {'id': element_id
                                            }).dialog({
                                                        modal: true,
                                                        minWidth: 800
                                                     });
                        self.element.val('');
                        var event_form = new openerp.base.FormView(self.view_manager, self.session, element_id, self.dataset, false);
                        event_form.start();
                });
                self.$input.val(self.element.data( "autocomplete" ).term);
                return true;
        }
    });
}

function call_Actions() {

}

function on_context_menu(evt, target, defaults){

    var $target = jQuery(target || evt.target);
    var kind = $target.attr('type');
    if (!(kind && $target.is(':input, :enabled'))) {
        return;
    }
    var $menu = jQuery('#contextmenu').show();
    if (!$menu.length) {
        $menu = jQuery('<div id="contextmenu" class="contextmenu">')
                .css({position: 'absolute'})
                .hover(showContextMenu, hideContextMenu)
                .appendTo(document.body).show();

        if (jQuery(document.documentElement).hasClass('ie')) {
            jQuery('<iframe id="contextmenu_frm" src="#" frameborder="0" scrolling="no">')
                    .css({position: 'absolute'})
                    .hide().appendTo(document.body);
        }
    }

    var src = $target.attr('id');
    if (kind == 'many2one' || kind == 'reference') {
        src = src.slice(0, -5);
    }
    var $src = jQuery('[id="' + src + '"]');

    var click_position = mousePositionDammit(evt);
    $menu.offset({top: 0, left: 0});
    $menu.offset({top: click_position.y - 5, left: click_position.x - 5});
    $menu.hide();
    makeContextMenu(src, kind, $src.attr('relation'), $src.val(), defaults);

    if(evt.stop) {
        evt.stop();
    }
    evt.stopPropagation();
    evt.preventDefault();
}


function makeContextMenu(id, kind, relation, val, defaults){
        var $tbody = jQuery('<tbody>');
        jQuery.each(defaults, function (_, default_) {
            jQuery('<tr>').append(jQuery('<td>').append(
                jQuery('<span>').click(function () {
                    hideContextMenu();
                    return eval(default_.action);
                }).text(default_.text))).appendTo($tbody);
        });

        var $menu = jQuery('#contextmenu');
        $menu.empty().append(
            jQuery('<table cellpadding="0" cellspacing="0">').append($tbody));

        var menu_width = $menu.width();
        var body_width = jQuery(document.body).width();
        if (parseInt($menu.css("left")) + menu_width > body_width) {
            $menu.offset({ left: body_width - menu_width - 10 });
        }
        showContextMenu();
}

function showContextMenu(){
    var $menu = jQuery('#contextmenu');
    var $ifrm = jQuery('#contextmenu_frm');
    console.log($menu, 8888888, $ifrm)
    $menu.show();
    if ($ifrm.length) {
        $ifrm.offset($menu.offset())
             .css({
                  width: $menu.offsetWidth(),
                  height: $menu.offsetHeight(),
                  zIndex: 6
              }).show();
    }
}

function hideContextMenu(){
    jQuery('#contextmenu, #contextmenu_frm').hide();
}

/**
 * Adapts mouse position on page for functions which may be bound using both
 * jQuery and MochiKit event handlers
 *
 * @param evt the library's events
 */
function mousePositionDammit(evt) {
    if(evt.mouse) {
        // mochikit
        return evt.mouse().page;
    }
    return {
        x: evt.pageX,
        y: evt.pageY
    }
}
