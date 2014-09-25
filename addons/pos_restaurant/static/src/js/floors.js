function openerp_restaurant_floors(instance,module){
    var _t = instance.web._t;

    module.PosModel.prototype.models.push({
        model: 'restaurant.floor',
        fields: ['name','background_image','table_ids'],
        domain: function(self){ return [['pos_config_id','=',self.config.id]] },
        loaded: function(self,floors){
            self.floors = floors;
            self.floors_by_id = {};
            for (var i = 0; i < floors.length; i++) {
                floors[i].tables = [];
                self.floors_by_id[floors[i].id] = floors[i];
            }
        },
    });

    module.PosModel.prototype.models.push({
        model: 'restaurant.table',
        fields: ['name','width','height','position_h','position_v','shape','floor_id','color'],
        loaded: function(self,tables){
            for (var i = 0; i < tables.length; i++) {
                var floor = self.floors_by_id[tables[i].floor_id[0]];
                if (floor) {
                    floor.tables.push(tables[i]);
                }
            }
        },
    });

    module.TableWidget = module.PosBaseWidget.extend({
        template: 'TableWidget',
        init: function(parent, options){
            this._super(parent, options)
            this.table    = options.table;
            this.selected = false;
            this.moved    = false;
            this.dragpos  = {x:0, y:0};
            this.handle_dragging = false;
            this.handle   = null;
        },
        event_position: function(event){
            if(event.touches && event.touches[0]){
                return {x: event.touches[0].screenX, y: event.touches[0].screenY};
            }else{
                return {x: event.screenX, y: event.screenY};
            }
        },
        click_handler: function(){
            var self = this;
            var floorplan = this.getParent();
            if (floorplan.editing) {
                setTimeout(function(){  // in a setTimeout to debounce with drag&drop
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
            }
        },
        dragstart_handler: function(event,$el,drag){
            if (this.selected && !this.handle_dragging) {
                this.dragging = true;
                this.dragpos  = { x: drag.offsetX, y: drag.offsetY };
            }
        },
        dragend_handler:   function(event,$el){
            this.dragging = false;
        },
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
        handle_dragstart_handler: function(event, $el, drag) {
            if (this.selected && !this.dragging) {
                this.handle_dragging = true;
                this.handle_dragpos  = this.event_position(event);
                this.handle          = drag.target;
            } 
        },
        handle_dragend_handler: function(event, $el, drag) {
            this.handle_dragging = false;
        },
        handle_dragmove_handler: function(event, $el, drag) {
            if (this.handle_dragging) {
                var pos  = this.event_position(event);
                var dx   = pos.x - this.handle_dragpos.x;
                var dy   = pos.y - this.handle_dragpos.y;

                this.handle_dragpos = pos;
                this.moved   = true;

                var cl     = this.handle.classList;

                var MIN_SIZE = 40;

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
            this.table.color = color;
            this.renderElement();
        },
        set_table_name: function(name){
            if (name) {
                this.table.name = name;
                this.renderElement();
            }
        },
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
                style['background-color'] = table.color;
            }
            if (table.height >= 150 && table.width >= 150) {
                style['font-size'] = '32px';
            } 

            return style;
        },
        table_style_str: function(){
            var style = this.table_style();
            var str = "";
            for (s in style) {
                str += s + ":" + style[s] + "; ";
            }
            return str;
        },
        select: function() {
            this.selected = true;
            this.renderElement();
        },
        deselect: function() {
            this.selected = false;
            this.renderElement();
            this.save_changes();
        },
        save_changes: function(){
            var self   = this;
            var model  = new instance.web.Model('restaurant.table');
            var fields = _.find(this.pos.models,function(model){ return model.model === 'restaurant.table'; }).fields;

            model.call('create_from_ui',[this.table]).then(function(table_id){
                model.query(fields).filter([['id','=',table_id]]).first().then(function(table){
                    for (field in table) {
                        self.table[field] = table[field];
                    }
                    self.renderElement();
                });
            });
        },
        trash: function(){
            var self  = this;
            var model = new instance.web.Model('restaurant.table');
            return model.call('create_from_ui',[{'active':false,'id':this.table.id}]).then(function(table_id){
                // Removing all references from the table and the table_widget in in the UI ... 
                // This should probably be cleaned. 
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
            });
        },
        renderElement: function(){
            var self = this;
            this._super();

            this.$el.on('mouseup',      function(event){ self.click_handler(event,$(this)); });
            this.$el.on('touchend',     function(event){ self.click_handler(event,$(this)); });
            this.$el.on('touchcancel',  function(event){ self.click_handler(event,$(this)); });
            this.$el.on('dragstart', function(event,drag){ self.dragstart_handler(event,$(this),drag); });
            this.$el.on('drag',      function(event,drag){ self.dragmove_handler(event,$(this),drag); });
            this.$el.on('dragend',   function(event,drag){ self.dragend_handler(event,$(this),drag); });
            
            var handles = this.$el.find('.table-handle');
            handles.on('dragstart',  function(event,drag){ self.handle_dragstart_handler(event,$(this),drag); });
            handles.on('drag',       function(event,drag){ self.handle_dragmove_handler(event,$(this),drag); });
            handles.on('dragend',    function(event,drag){ self.handle_dragend_handler(event,$(this),drag); });
        },
    });

    module.FloorScreenWidget = module.ScreenWidget.extend({
        template: 'FloorScreenWidget',
        show_leftpane: false,
        init: function(parent, options) {
            this._super(parent, options);
            this.floor = this.pos.floors[0];
            this.table_widgets = [];
            this.selected_table = null;
            this.editing = false;
        },
        show: function(){
            this._super();
            this.pos_widget.$('.order-selector').addClass('oe_invisible');
        },
        hide: function(){
            this._super();
            if (this.editing) { 
                this.toggle_editing();
            }
            this.pos_widget.$('.order-selector').removeClass('oe_invisible');
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
            }
        },
        background_image_url: function(floor) { 
            return '/website/image/restaurant.floor/'+floor.id+'/background_image';
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
            if (this.selected_table) {
                this.$('.color-picker').removeClass('oe_hidden');
            }
        },
        tool_colorpicker_pick: function(event,$el){
            if (this.selected_table) {
                this.selected_table.set_table_color($el[0].style['background-color']);
            }
        },
        tool_colorpicker_close: function(){
            this.$('.color-picker').addClass('oe_hidden');
        },
        tool_rename_table: function(){
            var self = this;
            if (this.selected_table) {
                this.pos_widget.screen_selector.show_popup('textinput',{
                    'message':_t('Table Name ?'),
                    'value': this.selected_table.table.name,
                    'confirm': function(value) {
                        self.selected_table.set_table_name(value);
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
                'position_v': 50,
                'position_h': 50,
                'width': 50,
                'height': 50,
                'name': 'T1',
                'shape': 'square',
            });
            this.select_table(tw);
        },
        create_table: function(params) {
            var table = {};
            for (var p in params) {
                table[p] = params[p];
            }

            delete table['id']; 
            table.floor_id = [this.floor.id,''];
            
            this.floor.tables.push(table);
            var tw = new module.TableWidget(this,{table: table});
                tw.appendTo('.floor-map');
            this.table_widgets.push(tw);
            return tw;
        },
        tool_trash_table: function(){
            var self = this;
            if (this.selected_table) {
                this.pos_widget.screen_selector.show_popup('confirm',{
                    'message':_t('Are you sure ?'),
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

            if (!this.editing) {
                this.deselect_tables();
            }
        },
        update_toolbar: function(){
            
            if (this.editing) {
                this.$('.edit-bar').removeClass('oe_hidden');
            } else {
                this.$('.edit-bar').addClass('oe_hidden');
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
                var tw = new module.TableWidget(this,{
                    table: this.floor.tables[i],
                });
                tw.appendTo(this.$('.floor-map'));
                this.table_widgets.push(tw);
            }

            this.$('.floor-selector .button').click(function(event){
                self.click_floor_button(event,$(this));
            });

            this.$('.edit-button.shape').click(function(event){
                self.tool_shape_action();
            });

            this.$('.edit-button.color').click(function(event){
                self.tool_colorpicker_open();
            });

            this.$('.edit-button.dup-table').click(function(event){
                self.tool_duplicate_table();
            });

            this.$('.edit-button.new-table').click(function(event){
                self.tool_new_table();
            });

            this.$('.edit-button.rename').click(function(event){
                self.tool_rename_table();
            });

            this.$('.edit-button.trash').click(function(event){
                self.tool_trash_table();
            });
            
            this.$('.color-picker .close-picker').click(function(event){
                self.tool_colorpicker_close();
                event.stopPropagation();
            });

            this.$('.color-picker .color').click(function(event){
                self.tool_colorpicker_pick(event,$(this));
                self.tool_colorpicker_close();
                event.stopPropagation();
            });

            this.$('.edit-button.editing').click(function(){
                self.toggle_editing();
            });

            this.$('.floor-map').click(function(event){
                if (event.target === self.$('.floor-map')[0]) {
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

    module.PosWidget.include({
        build_widgets: function(){
            var self = this;
            this._super();
            if (this.pos.floors.length > 0) {
                this.floors_screen = new module.FloorScreenWidget(this,{});
                this.floors_screen.appendTo(this.$('.screens'));
                this.screen_selector.add_screen('floors',this.floors_screen);
                this.screen_selector.change_default_screen('floors');
            }
        },
    });

}
