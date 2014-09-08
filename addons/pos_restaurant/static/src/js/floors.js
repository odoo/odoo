function openerp_restaurant_floors(instance,module){

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

    module.FloorScreenWidget = module.ScreenWidget.extend({
        template: 'FloorScreenWidget',
        show_leftpane: false,

        init: function(parent, options) {
            this._super(parent, options);
            this.floor = this.pos.floors[0];
        },
        click_floor_button: function(event,$el){
            var floor = this.pos.floors_by_id[$el.data('id')];
            if (floor !== this.floor) {
                this.floor = floor;
                this.renderElement();
            }
        },
        table_style: function(table){
            function unit(val){ return Math.floor(val * 10) + 'px'; }
            var str = "";
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
            for (s in style) {
                str += s + ":" + style[s] + "; ";
            }
            return str;
        },
        renderElement: function(){
            var self = this;
            this._super();
            this.$('.floor-selector .button').click(function(event){
                self.click_floor_button(event,$(this));
            });
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
