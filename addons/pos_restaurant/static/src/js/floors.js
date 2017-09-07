odoo.define('pos_restaurant.floors', function (require) {
"use strict";

var PosBaseWidget = require('point_of_sale.BaseWidget');
var chrome = require('point_of_sale.chrome');
var gui = require('point_of_sale.gui');
var models = require('point_of_sale.models');
var screens = require('point_of_sale.screens');
var core = require('web.core');
var Model = require('web.DataModel');

var QWeb = core.qweb;
var _t = core._t;

// At POS Startup, load the floors, and add them to the pos model
models.load_models({
    model: 'restaurant.floor',
    fields: ['name','background_color','table_ids','sequence'],
    domain: function(self){ return [['pos_config_id','=',self.config.id]]; },
    loaded: function(self,floors){
        self.floors = floors;
        self.floors_by_id = {};
        for (var i = 0; i < floors.length; i++) {
            floors[i].tables = [];
            self.floors_by_id[floors[i].id] = floors[i];
        }

        // Make sure they display in the correct order
        self.floors = self.floors.sort(function(a,b){ return a.sequence - b.sequence; });

        // Ignore floorplan features if no floor specified.
        self.config.iface_floorplan = !!self.floors.length;
    },
});

// At POS Startup, after the floors are loaded, load the tables, and associate
// them with their floor.
models.load_models({
    model: 'restaurant.table',
    fields: ['name','width','height','position_h','position_v','shape','floor_id','color','seats'],
    loaded: function(self,tables){
        self.tables_by_id = {};
        for (var i = 0; i < tables.length; i++) {
            self.tables_by_id[tables[i].id] = tables[i];
            var floor = self.floors_by_id[tables[i].floor_id[0]];
            if (floor) {
                floor.tables.push(tables[i]);
                tables[i].floor = floor;
            }
        }
    },
});

// The Table GUI element, should always be a child of the FloorScreenWidget
var TableWidget = PosBaseWidget.extend({
    template: 'TableWidget',
    init: function(parent, options){
        this._super(parent, options);
        this.table    = options.table;
        this.selected = false;
        this.moved    = false;
        this.dragpos  = {x:0, y:0};
        this.handle_dragging = false;
        this.handle   = null;
    },
    // computes the absolute position of a DOM mouse event, used
    // when resizing tables
    event_position: function(event){
        if(event.touches && event.touches[0]){
            return {x: event.touches[0].screenX, y: event.touches[0].screenY};
        }else{
            return {x: event.screenX, y: event.screenY};
        }
    },
    // when a table is clicked, go to the table's orders
    // but if we're editing, we select/deselect it.
    click_handler: function(){
        var self = this;
        var floorplan = this.getParent();
        if (floorplan.editing) {
            setTimeout(function(){  // in a setTimeout to debounce with drag&drop start
                if (!self.dragging) {
                    if (self.moved) {
                        self.moved = false;
                    } else if (!self.selected) {
                        self.getParent().select_table(self);
                    } else {
                        self.getParent().deselect_tables();
                    }
                }
            },50);
        } else {
            floorplan.pos.set_table(this.table);
        }
    },
    // drag and drop for moving the table, at drag start
    dragstart_handler: function(event,$el,drag){
        if (this.selected && !this.handle_dragging) {
            this.dragging = true;
            this.dragpos  = { x: drag.offsetX, y: drag.offsetY };
        }
    },
    // drag and drop for moving the table, at drag end
    dragend_handler:   function(){
        this.dragging = false;
    },
    // drag and drop for moving the table, at every drop movement.
    dragmove_handler: function(event,$el,drag){
        if (this.dragging) {
            var dx   = drag.offsetX - this.dragpos.x;
            var dy   = drag.offsetY - this.dragpos.y;

            this.dragpos = { x: drag.offsetX, y: drag.offsetY };
            this.moved   = true;

            this.table.position_v += dy;
            this.table.position_h += dx;

            $el.css(this.table_style());
        }
    },
    // drag and dropping the resizing handles
    handle_dragstart_handler: function(event, $el, drag) {
        if (this.selected && !this.dragging) {
            this.handle_dragging = true;
            this.handle_dragpos  = this.event_position(event);
            this.handle          = drag.target;
        }
    },
    handle_dragend_handler: function() {
        this.handle_dragging = false;
    },
    handle_dragmove_handler: function(event) {
        if (this.handle_dragging) {
            var pos  = this.event_position(event);
            var dx   = pos.x - this.handle_dragpos.x;
            var dy   = pos.y - this.handle_dragpos.y;

            this.handle_dragpos = pos;
            this.moved   = true;

            var cl     = this.handle.classList;

            var MIN_SIZE = 40;  // smaller than this, and it becomes impossible to edit.

            var tw = Math.max(MIN_SIZE, this.table.width);
            var th = Math.max(MIN_SIZE, this.table.height);
            var tx = this.table.position_h;
            var ty = this.table.position_v;

            if (cl.contains('left') && tw - dx >= MIN_SIZE) {
                tw -= dx;
                tx += dx;
            } else if (cl.contains('right') && tw + dx >= MIN_SIZE) {
                tw += dx;
            }

            if (cl.contains('top') && th - dy >= MIN_SIZE) {
                th -= dy;
                ty += dy;
            } else if (cl.contains('bottom') && th + dy >= MIN_SIZE) {
                th += dy;
            }

            this.table.width  = tw;
            this.table.height = th;
            this.table.position_h = tx;
            this.table.position_v = ty;

            this.$el.css(this.table_style());
        }
    },
    set_table_color: function(color){
        this.table.color = _.escape(color);
        this.$el.css({'background': this.table.color});
    },
    set_table_name: function(name){
        if (name) {
            this.table.name = name;
            this.renderElement();
        }
    },
    set_table_seats: function(seats){
        if (seats) {
            this.table.seats = Number(seats);
            this.renderElement();
        }
    },
    // The table's positioning is handled via css absolute positioning,
    // which is handled here.
    table_style: function(){
        var table = this.table;
        function unit(val){ return '' + val + 'px'; }
        var style = {
            'width':        unit(table.width),
            'height':       unit(table.height),
            'line-height':  unit(table.height),
            'margin-left':  unit(-table.width/2),
            'margin-top':   unit(-table.height/2),
            'top':          unit(table.position_v + table.height/2),
            'left':         unit(table.position_h + table.width/2),
            'border-radius': table.shape === 'round' ?
                    unit(Math.max(table.width,table.height)/2) : '3px',
        };
        if (table.color) {
            style.background = table.color;
        }
        if (table.height >= 150 && table.width >= 150) {
            style['font-size'] = '32px';
        }

        return style;
    },
    // convert the style dictionary to a ; separated string for inclusion in templates
    table_style_str: function(){
        var style = this.table_style();
        var str = "";
        var s;
        for (s in style) {
            str += s + ":" + style[s] + "; ";
        }
        return str;
    },
    // select the table (should be called via the floorplan)
    select: function() {
        this.selected = true;
        this.renderElement();
    },
    // deselect the table (should be called via the floorplan)
    deselect: function() {
        this.selected = false;
        this.renderElement();
        this.save_changes();
    },
    // sends the table's modification to the server
    save_changes: function(){
        var self   = this;
        var model  = new Model('restaurant.table');
        var fields = _.find(this.pos.models,function(model){ return model.model === 'restaurant.table'; }).fields;

        // we need a serializable copy of the table, containing only the fields defined on the server
        var serializable_table = {};
        for (var i = 0; i < fields.length; i++) {
            if (typeof this.table[fields[i]] !== 'undefined') {
                serializable_table[fields[i]] = this.table[fields[i]];
            }
        }
        // and the id ...
        serializable_table.id = this.table.id;

        model.call('create_from_ui',[serializable_table]).then(function(table_id){
            model.query(fields).filter([['id','=',table_id]]).first().then(function(table){
                for (var field in table) {
                    self.table[field] = table[field];
                }
                self.renderElement();
            });
        }, function(err,event) {
            self.gui.show_popup('error',{
                'title':_t('Changes could not be saved'),
                'body': _t('You must be connected to the internet to save your changes.'),
            });
            event.stopPropagation();
            event.preventDefault();
        });
    },
    // destroy the table.  We do not really destroy it, we set it
    // to inactive so that it doesn't show up anymore, but it still
    // available on the database for the orders that depend on it.
    trash: function(){
        var self  = this;
        var model = new Model('restaurant.table');
        return model.call('create_from_ui',[{'active':false,'id':this.table.id}]).then(function(table_id){
            // Removing all references from the table and the table_widget in in the UI ...
            for (var i = 0; i < self.pos.floors.length; i++) {
                var floor = self.pos.floors[i];
                for (var j = 0; j < floor.tables.length; j++) {
                    if (floor.tables[j].id === table_id) {
                        floor.tables.splice(j,1);
                        break;
                    }
                }
            }
            var floorplan = self.getParent();
            for (var i = 0; i < floorplan.table_widgets.length; i++) {
                if (floorplan.table_widgets[i] === self) {
                    floorplan.table_widgets.splice(i,1);
                }
            }
            if (floorplan.selected_table === self) {
                floorplan.selected_table = null;
            }
            floorplan.update_toolbar();
            self.destroy();
        }, function(err, event) {
            self.gui.show_popup('error', {
                'title':_t('Changes could not be saved'),
                'body': _t('You must be connected to the internet to save your changes.'),
            });
            event.stopPropagation();
            event.preventDefault();
        });
    },
    get_notifications: function(){  //FIXME : Make this faster
        var orders = this.pos.get_table_orders(this.table);
        var notifications = {};
        for (var i = 0; i < orders.length; i++) {
            if (orders[i].hasChangesToPrint()) {
                notifications.printing = true;
                break;
            } else if (orders[i].hasSkippedChanges()) {
                notifications.skipped  = true;
            }
        }
        return notifications;
    },
        update_click_handlers: function(editing){
            var self = this;
            this.$el.off('mouseup touchend touchcancel click dragend');

            if (editing) {
                this.$el.on('mouseup touchend touchcancel', function(event){ self.click_handler(event,$(this)); });
            } else {
                this.$el.on('click dragend', function(event){ self.click_handler(event,$(this)); });
            }
        },
    renderElement: function(){
        var self = this;
        this.order_count    = this.pos.get_table_orders(this.table).length;
        this.customer_count = this.pos.get_customer_count(this.table);
        this.fill           = Math.min(1,Math.max(0,this.customer_count / this.table.seats));
        this.notifications  = this.get_notifications();
        this._super();

        this.update_click_handlers();

        this.$el.on('dragstart', function(event,drag){ self.dragstart_handler(event,$(this),drag); });
        this.$el.on('drag',      function(event,drag){ self.dragmove_handler(event,$(this),drag); });
        this.$el.on('dragend',   function(event,drag){ self.dragend_handler(event,$(this),drag); });

        var handles = this.$el.find('.table-handle');
        handles.on('dragstart',  function(event,drag){ self.handle_dragstart_handler(event,$(this),drag); });
        handles.on('drag',       function(event,drag){ self.handle_dragmove_handler(event,$(this),drag); });
        handles.on('dragend',    function(event,drag){ self.handle_dragend_handler(event,$(this),drag); });
    },
});

// The screen that allows you to select the floor, see and select the table,
// as well as edit them.
var FloorScreenWidget = screens.ScreenWidget.extend({
    template: 'FloorScreenWidget',

    // Ignore products, discounts, and client barcodes
    barcode_product_action: function(code){},
    barcode_discount_action: function(code){},
    barcode_client_action: function(code){},

    init: function(parent, options) {
        this._super(parent, options);
        this.floor = this.pos.floors[0];
        this.table_widgets = [];
        this.selected_table = null;
        this.editing = false;
    },
    hide: function(){
        this._super();
        if (this.editing) {
            this.toggle_editing();
        }
        this.chrome.widget.order_selector.show();
    },
    show: function(){
        this._super();
        this.chrome.widget.order_selector.hide();
        for (var i = 0; i < this.table_widgets.length; i++) {
            this.table_widgets[i].renderElement();
        }
        this.check_empty_floor();
    },
    click_floor_button: function(event,$el){
        var floor = this.pos.floors_by_id[$el.data('id')];
        if (floor !== this.floor) {
            if (this.editing) {
                this.toggle_editing();
            }
            this.floor = floor;
            this.selected_table = null;
            this.renderElement();
            this.check_empty_floor();
        }
    },
    background_image_url: function(floor) {
        return '/web/image?model=restaurant.floor&id='+floor.id+'&field=background_image';
    },
    get_floor_style: function() {
        var style = "";
        if (this.floor.background_image) {
            style += "background-image: url(" + this.background_image_url(this.floor) + "); ";
        }
        if (this.floor.background_color) {
            style += "background-color: " + _.escape(this.floor.background_color) + ";";
        }
        return style;
    },
    set_background_color: function(background) {
        var self = this;
        this.floor.background_color = background;
        (new Model('restaurant.floor'))
            .call('write',[[this.floor.id], {'background_color': background}]).fail(function(err, event){
                self.gui.show_popup('error',{
                    'title':_t('Changes could not be saved'),
                    'body': _t('You must be connected to the internet to save your changes.'),
                });
                event.stopPropagation();
                event.preventDefault();
            });
        this.$('.floor-map').css({"background-color": _.escape(background)});
    },
    deselect_tables: function(){
        for (var i = 0; i < this.table_widgets.length; i++) {
            var table = this.table_widgets[i];
            if (table.selected) {
                table.deselect();
            }
        }
        this.selected_table = null;
        this.update_toolbar();
    },
    select_table: function(table_widget){
        if (!table_widget.selected) {
            this.deselect_tables();
            table_widget.select();
            this.selected_table = table_widget;
            this.update_toolbar();
        }
    },
    tool_shape_action: function(){
        if (this.selected_table) {
            var table = this.selected_table.table;
            if (table.shape === 'square') {
                table.shape = 'round';
            } else {
                table.shape = 'square';
            }
            this.selected_table.renderElement();
            this.update_toolbar();
        }
    },
    tool_colorpicker_open: function(){
        this.$('.color-picker').addClass('oe_hidden');
        if (this.selected_table) {
            this.$('.color-picker.fg-picker').removeClass('oe_hidden');
        } else {
            this.$('.color-picker.bg-picker').removeClass('oe_hidden');
        }
    },
    tool_colorpicker_pick: function(event,$el){
        if (this.selected_table) {
            this.selected_table.set_table_color($el[0].style['background-color']);
        } else {
            this.set_background_color($el[0].style['background-color']);
        }
    },
    tool_colorpicker_close: function(){
        this.$('.color-picker').addClass('oe_hidden');
    },
    tool_rename_table: function(){
        var self = this;
        if (this.selected_table) {
            this.gui.show_popup('textinput',{
                'title':_t('Table Name ?'),
                'value': this.selected_table.table.name,
                'confirm': function(value) {
                    self.selected_table.set_table_name(value);
                },
            });
        }
    },
    tool_change_seats: function(){
        var self = this;
        if (this.selected_table) {
            this.gui.show_popup('number',{
                'title':_t('Number of Seats ?'),
                'cheap': true,
                'value': this.selected_table.table.seats,
                'confirm': function(value) {
                    self.selected_table.set_table_seats(value);
                },
            });
        }
    },
    tool_duplicate_table: function(){
        if (this.selected_table) {
            var tw = this.create_table(this.selected_table.table);
            tw.table.position_h += 10;
            tw.table.position_v += 10;
            tw.save_changes();
            this.select_table(tw);
        }
    },
    tool_new_table: function(){
        var tw = this.create_table({
            'position_v': 100,
            'position_h': 100,
            'width': 75,
            'height': 75,
            'shape': 'square',
            'seats': 1,
        });
        tw.save_changes();
        this.select_table(tw);
        this.check_empty_floor();
    },
    new_table_name: function(name){
        if (name) {
            var num = Number((name.match(/\d+/g) || [])[0] || 0);
            var str = (name.replace(/\d+/g,''));
            var n   = {num: num, str:str};
                n.num += 1;
            this.last_name = n;
        } else if (this.last_name) {
            this.last_name.num += 1;
        } else {
            this.last_name = {num: 1, str:'T'};
        }
        return '' + this.last_name.str + this.last_name.num;
    },
    create_table: function(params) {
        var table = {};
        for (var p in params) {
            table[p] = params[p];
        }

        table.name = this.new_table_name(params.name);

        delete table.id;
        table.floor_id = [this.floor.id,''];
        table.floor = this.floor;

        this.floor.tables.push(table);
        var tw = new TableWidget(this,{table: table});
            tw.appendTo('.floor-map .tables');
        this.table_widgets.push(tw);
        return tw;
    },
    tool_trash_table: function(){
        var self = this;
        if (this.selected_table) {
            this.gui.show_popup('confirm',{
                'title':  _t('Are you sure ?'),
                'comment':_t('Removing a table cannot be undone'),
                'confirm': function(){
                    self.selected_table.trash();
                },
            });
        }
    },
    toggle_editing: function(){
        this.editing = !this.editing;
        this.update_toolbar();
            this.update_table_click_handlers();

        if (!this.editing) {
            this.deselect_tables();
            }
        },
        update_table_click_handlers: function(){
            for (var i = 0; i < this.table_widgets.length; ++i) {
                if (this.editing) {
                    this.table_widgets[i].update_click_handlers("editing");
                } else {
                    this.table_widgets[i].update_click_handlers();
                }
        }
    },
    check_empty_floor: function(){
        if (!this.floor.tables.length) {
            if (!this.editing) {
                this.toggle_editing();
            }
            this.$('.empty-floor').removeClass('oe_hidden');
        } else {
            this.$('.empty-floor').addClass('oe_hidden');
        }
    },
    update_toolbar: function(){

        if (this.editing) {
            this.$('.edit-bar').removeClass('oe_hidden');
            this.$('.edit-button.editing').addClass('active');
        } else {
            this.$('.edit-bar').addClass('oe_hidden');
            this.$('.edit-button.editing').removeClass('active');
        }

        if (this.selected_table) {
            this.$('.needs-selection').removeClass('disabled');
            var table = this.selected_table.table;
            if (table.shape === 'square') {
                this.$('.button-option.square').addClass('oe_hidden');
                this.$('.button-option.round').removeClass('oe_hidden');
            } else {
                this.$('.button-option.square').removeClass('oe_hidden');
                this.$('.button-option.round').addClass('oe_hidden');
            }
        } else {
            this.$('.needs-selection').addClass('disabled');
        }
        this.tool_colorpicker_close();
    },
    renderElement: function(){
        var self = this;

        // cleanup table widgets from previous renders
        for (var i = 0; i < this.table_widgets.length; i++) {
            this.table_widgets[i].destroy();
        }

        this.table_widgets = [];

        this._super();

        for (var i = 0; i < this.floor.tables.length; i++) {
            var tw = new TableWidget(this,{
                table: this.floor.tables[i],
            });
            tw.appendTo(this.$('.floor-map .tables'));
            this.table_widgets.push(tw);
        }

        this.$('.floor-selector .button').click(function(event){
            self.click_floor_button(event,$(this));
        });

        this.$('.edit-button.shape').click(function(){
            self.tool_shape_action();
        });

        this.$('.edit-button.color').click(function(){
            self.tool_colorpicker_open();
        });

        this.$('.edit-button.dup-table').click(function(){
            self.tool_duplicate_table();
        });

        this.$('.edit-button.new-table').click(function(){
            self.tool_new_table();
        });

        this.$('.edit-button.rename').click(function(){
            self.tool_rename_table();
        });

        this.$('.edit-button.seats').click(function(){
            self.tool_change_seats();
        });

        this.$('.edit-button.trash').click(function(){
            self.tool_trash_table();
        });

        this.$('.color-picker .close-picker').click(function(event){
            self.tool_colorpicker_close();
            event.stopPropagation();
        });

        this.$('.color-picker .color').click(function(event){
            self.tool_colorpicker_pick(event,$(this));
            event.stopPropagation();
        });

        this.$('.edit-button.editing').click(function(){
            self.toggle_editing();
        });

        this.$('.floor-map,.floor-map .tables').click(function(event){
            if (event.target === self.$('.floor-map')[0] ||
                event.target === self.$('.floor-map .tables')[0]) {
                self.deselect_tables();
            }
        });

        this.$('.color-picker .close-picker').click(function(event){
            self.tool_colorpicker_close();
            event.stopPropagation();
        });

        this.update_toolbar();

    },
});

gui.define_screen({
    'name': 'floors',
    'widget': FloorScreenWidget,
    'condition': function(){
        return this.pos.config.iface_floorplan;
    },
});

// Add the FloorScreen to the GUI, and set it as the default screen
chrome.Chrome.include({
    build_widgets: function(){
        this._super();
        if (this.pos.config.iface_floorplan) {
            this.gui.set_startup_screen('floors');
        }
    },
});

// New orders are now associated with the current table, if any.
var _super_order = models.Order.prototype;
models.Order = models.Order.extend({
    initialize: function() {
        _super_order.initialize.apply(this,arguments);
        if (!this.table) {
            this.table = this.pos.table;
        }
        this.customer_count = this.customer_count || 1;
        this.save_to_db();
    },
    export_as_JSON: function() {
        var json = _super_order.export_as_JSON.apply(this,arguments);
        json.table     = this.table ? this.table.name : undefined;
        json.table_id  = this.table ? this.table.id : false;
        json.floor     = this.table ? this.table.floor.name : false;
        json.floor_id  = this.table ? this.table.floor.id : false;
        json.customer_count = this.customer_count;
        return json;
    },
    init_from_JSON: function(json) {
        _super_order.init_from_JSON.apply(this,arguments);
        this.table = this.pos.tables_by_id[json.table_id];
        this.floor = this.table ? this.pos.floors_by_id[json.floor_id] : undefined;
        this.customer_count = json.customer_count || 1;
    },
    export_for_printing: function() {
        var json = _super_order.export_for_printing.apply(this,arguments);
        json.table = this.table ? this.table.name : undefined;
        json.floor = this.table ? this.table.floor.name : undefined;
        json.customer_count = this.get_customer_count();
        return json;
    },
    get_customer_count: function(){
        return this.customer_count;
    },
    set_customer_count: function(count) {
        this.customer_count = Math.max(count,0);
        this.trigger('change');
    },
});

// We need to modify the OrderSelector to hide itself when we're on
// the floor plan
chrome.OrderSelectorWidget.include({
    floor_button_click_handler: function(){
        this.pos.set_table(null);
    },
    hide: function(){
        this.$el.addClass('oe_invisible');
    },
    show: function(){
        this.$el.removeClass('oe_invisible');
    },
    renderElement: function(){
        var self = this;
        this._super();
        if (this.pos.config.iface_floorplan) {
            if (this.pos.get_order()) {
                if (this.pos.table && this.pos.table.floor) {
                    this.$('.orders').prepend(QWeb.render('BackToFloorButton',{table: this.pos.table, floor:this.pos.table.floor}));
                    this.$('.floor-button').click(function(){
                        self.floor_button_click_handler();
                    });
                }
                this.$el.removeClass('oe_invisible');
            } else {
                this.$el.addClass('oe_invisible');
            }
        }
    },
});

// We need to change the way the regular UI sees the orders, it
// needs to only see the orders associated with the current table,
// and when an order is validated, it needs to go back to the floor map.
//
// And when we change the table, we must create an order for that table
// if there is none.
var _super_posmodel = models.PosModel.prototype;
models.PosModel = models.PosModel.extend({
    initialize: function(session, attributes) {
        this.table = null;
        return _super_posmodel.initialize.call(this,session,attributes);
    },

    transfer_order_to_different_table: function () {
        this.order_to_transfer_to_different_table = this.get_order();

        // go to 'floors' screen, this will set the order to null and
        // eventually this will cause the gui to go to its
        // default_screen, which is 'floors'
        this.set_table(null);
    },

    // changes the current table.
    set_table: function(table) {
        if (!table) { // no table ? go back to the floor plan, see ScreenSelector
            this.set_order(null);
        } else if (this.order_to_transfer_to_different_table) {
            this.order_to_transfer_to_different_table.table = table;
            this.order_to_transfer_to_different_table.save_to_db();
            this.order_to_transfer_to_different_table = null;

            // set this table
            this.set_table(table);

        } else {
            this.table = table;
            var orders = this.get_order_list();
            if (orders.length) {
                this.set_order(orders[0]); // and go to the first one ...
            } else {
                this.add_new_order();  // or create a new order with the current table
            }
        }
    },

    // if we have tables, we do not load a default order, as the default order will be
    // set when the user selects a table.
    set_start_order: function() {
        if (!this.config.iface_floorplan) {
            _super_posmodel.set_start_order.apply(this,arguments);
        }
    },

    // we need to prevent the creation of orders when there is no
    // table selected.
    add_new_order: function() {
        if (this.config.iface_floorplan) {
            if (this.table) {
                return _super_posmodel.add_new_order.call(this);
            } else {
                console.warn("WARNING: orders cannot be created when there is no active table in restaurant mode");
                return undefined;
            }
        } else {
            return _super_posmodel.add_new_order.apply(this,arguments);
        }
    },


    // get the list of unpaid orders (associated to the current table)
    get_order_list: function() {
        var orders = _super_posmodel.get_order_list.call(this);
        if (!this.config.iface_floorplan) {
            return orders;
        } else if (!this.table) {
            return [];
        } else {
            var t_orders = [];
            for (var i = 0; i < orders.length; i++) {
                if ( orders[i].table === this.table) {
                    t_orders.push(orders[i]);
                }
            }
            return t_orders;
        }
    },

    // get the list of orders associated to a table. FIXME: should be O(1)
    get_table_orders: function(table) {
        var orders   = _super_posmodel.get_order_list.call(this);
        var t_orders = [];
        for (var i = 0; i < orders.length; i++) {
            if (orders[i].table === table) {
                t_orders.push(orders[i]);
            }
        }
        return t_orders;
    },

    // get customer count at table
    get_customer_count: function(table) {
        var orders = this.get_table_orders(table);
        var count  = 0;
        for (var i = 0; i < orders.length; i++) {
            count += orders[i].get_customer_count();
        }
        return count;
    },

    // When we validate an order we go back to the floor plan.
    // When we cancel an order and there is multiple orders
    // on the table, stay on the table.
    on_removed_order: function(removed_order,index,reason){
        if (this.config.iface_floorplan) {
            var order_list = this.get_order_list();
            if( (reason === 'abandon' || removed_order.temporary) && order_list.length > 0){
                this.set_order(order_list[index] || order_list[order_list.length -1]);
            }else{
                // back to the floor plan
                this.set_table(null);
            }
        } else {
            _super_posmodel.on_removed_order.apply(this,arguments);
        }
    },


});

var TableGuestsButton = screens.ActionButtonWidget.extend({
    template: 'TableGuestsButton',
    guests: function() {
        if (this.pos.get_order()) {
            return this.pos.get_order().customer_count;
        } else {
            return 0;
        }
    },
    button_click: function() {
        var self = this;
        this.gui.show_popup('number', {
            'title':  _t('Guests ?'),
            'cheap': true,
            'value':   this.pos.get_order().customer_count,
            'confirm': function(value) {
                value = Math.max(1,Number(value));
                self.pos.get_order().set_customer_count(value);
                self.renderElement();
            },
        });
    },
});

screens.OrderWidget.include({
    update_summary: function(){
        this._super();
        if (this.getParent().action_buttons &&
            this.getParent().action_buttons.guests) {
            this.getParent().action_buttons.guests.renderElement();
        }
    },
});

screens.define_action_button({
    'name': 'guests',
    'widget': TableGuestsButton,
    'condition': function(){
        return this.pos.config.iface_floorplan;
    },
});

var TransferOrderButton = screens.ActionButtonWidget.extend({
    template: 'TransferOrderButton',
    button_click: function() {
        this.pos.transfer_order_to_different_table();
    },
});

screens.define_action_button({
    'name': 'transfer',
    'widget': TransferOrderButton,
    'condition': function(){
        return this.pos.config.iface_floorplan;
    },
});

return {
    TableGuestsButton: TableGuestsButton,
    TransferOrderButton:TransferOrderButton,
    TableWidget: TableWidget,
    FloorScreenWidget: FloorScreenWidget,
};

});
