
function openerp_picking_widgets(instance){
    var module = instance.stock;

    module.PickingEditorWidget = instance.web.Widget.extend({
        template: 'PickingEditorWidget',
        init: function(parent,options){
            this._super(parent,options);
        },
        get_header: function(){
            var model = this.getParent();
            return 'Picking: '+model.picking.name;
        },
        get_rows: function(){
            var model = this.getParent();
            var rows = [];
            console.log('Parent:', this.getParent());
            
            _.each( model.movelines, function(moveline){
                console.log('Moveline:',moveline);
                rows.push({
                    cols: { product: moveline.product_id[1],
                            qty: moveline.product_qty,
                            rem: moveline.remaining_qty,
                            uom: moveline.product_uom[1],
                            loc: moveline.location_id[1],
                            stat: moveline.state 
                    },
                    classes: (moveline.qty_remaining < 0 ? 'oe_invalid' : '')
                });
            });
            
            return rows;
        },
    });

    module.PackageEditorWidget = instance.web.Widget.extend({
        template: 'PackageEditorWidget',
        get_header: function(){
            return this._header || 'Package: 032 ';
        },
        get_rows: function(){
            var model = this.getParent();
            var rows = [];
            
            _.each( model.operations, function(op){
                rows.push({
                    cols: {
                        product: op.product_id[1],
                        uom: op.product_uom ? product_uom[1] : 'false',
                        qty: op.product_qty,
                    }
                });
            });

            return rows;
        },
    });

    module.PackageSelectorWidget = instance.web.Widget.extend({
        template: 'PackageSelectorWidget',
        get_header: function(){
            return this._header || 'Package Selector';
        },
        get_rows: function(){
            return this._rows || [
                { cols: { pack:'abc', qty:12  },   },
                { cols: { pack:'def', qty:500 }, classes: ''   },
                { cols: { pack:'ghi', qty:1   },   },
            ];
        },
    });

    module.PickingMainWidget = instance.web.Widget.extend({
        template: 'PickingMainWidget',
        init: function(parent,params){
            this._super(parent,params);
            var self = this;

            this.picking = null;
            this.movelines = null;
            this.operations = null;
            
            window.pickwidget = this;
            
            console.log('Action params:', params);

            this.loaded = new instance.web.Model('stock.picking.in')
                .query()
                .all()
                .then(function(picking_in){
                    self.picking = picking_in[0];
                    console.log('Picking In:',picking_in);
                    
                    return new instance.web.Model('stock.move').call('read',[self.picking.move_lines, []]);
                }).then(function(movelines){
                    self.movelines = movelines;
                    console.log('Move Lines:',movelines);

                    return new instance.web.Model('stock.pack.operation').call('read',[self.picking.pack_operation_ids, []]);
                }).then(function(operations){
                    self.operations = operations;
                    console.log('Operations:',self.operations);
                });

        },
        start: function(){
            var self = this;
            instance.webclient.set_content_full_screen(true);

            this.$('.js_pick_quit').click(function(){ self.quit(); });

            $.when(this.loaded).done(function(){
                self.picking_editor = new module.PickingEditorWidget(self);
                self.picking_editor.replace(self.$('.oe_placeholder_picking_editor'));

                self.package_editor = new module.PackageEditorWidget(self);
                self.package_editor.replace(self.$('.oe_placeholder_package_editor'));

                self.package_selector = new module.PackageSelectorWidget(self);
                self.package_selector.replace(self.$('.oe_placeholder_package_selector'));
            });


            return this._super();
        },
        scan: function(ean){
            var self = this;
            new instance.web.Model('stock.picking')
                .call('get_barcode_and_return_todo_stuff', [this.picking.id, ean])
                .then(function(todo){

                    _.each(todo.moves_to_update, function(update){
                        if(update[0] === 0){ // create a new line
                            console.log('New line:',update);
                            self.movelines.push(update[2]);

                        }else if(update[0] === 1){ // update a line
                            console.log('Update line:',update);
                            for(var i = 0; i < self.movelines.length; i++){
                                if( self.movelines[i].id === update[1]){
                                    for(field in update[2]){
                                        self.movelines[i][field] = update[2][field];
                                    }
                                    break;
                                }
                            }
                        }else if(update[0] === 2){ // remove a line
                            console.log('Remove line:',update);
                            for(var i = 0; i < self.movelines.length; i++){
                                if( self.movelines[i].id === update[1] ){
                                    self.movelines.splice(i,1);
                                    break;
                                }
                            }
                        }
                        
                    });
                    
                    self.picking_editor.renderElement();

                    new instance.web.Model('stock.pack.operation').call('read',[self.picking.pack_operation_ids, []])
                        .then(function(operations){
                            self.operations = operations;
                            self.package_editor.renderElement();
                            console.log('Updated the operations list !');
                        });
                });
        },
        quit: function(){
            console.log('Quit');
            instance.webclient.set_content_full_screen(false);
            window.location = '/'; // FIXME THIS IS SHIT NIV WILL KILL YOU (BY MULTIPLE FACE-STABBING) IF YOU MERGE THIS IN TRUNK
        },
    });
}
