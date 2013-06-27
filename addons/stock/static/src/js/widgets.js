
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

            _.each( model.movelines, function(moveline){
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
            var model = this.getParent();
            var current_package_id = instance.session.user_context.current_package_id;
            return current_package_id ? 'Current Operations for package: ' + current_package_id[1] : 'Current Operations';
        },
        get_rows: function(){
            var current_package_id = instance.session.user_context.current_package_id;
            var model = this.getParent();
            var rows = [];
            
            _.each( model.operations, function(op){
                if(current_package_id && op.package_id !== current_package_id){
                    return;
                }
                rows.push({
                    cols: {
                        product: op.product_id[1],
                        uom: op.product_uom ? product_uom[1] : '',
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
            return this._header || 'Packages:';
        },
        get_rows: function(){
            var model = this.getParent();
            var rows = [];
            _.each( model.packages, function(pack){
                rows.push({
                    cols:{ pack: pack.name},
                    id: pack.id
                });
            });
            return rows;
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
            this.packages = null;
            
            window.pickwidget = this;
            
            console.log('Action params:', params);
            console.log('Session:',instance.session);

            this.loaded =  this.load();
        },
        load: function(picking_id){
            var self = this;

            if(picking_id){
                var picking = new instance.web.Model('stock.picking.in').call('read',[[picking_id], []]);
            }else{ 
                var picking = new instance.web.Model('stock.picking.in').query().first();
            }

            var loaded = picking.then(function(picking){
                    self.picking = picking instanceof Array ? picking[0] : picking;
                    console.log('Picking:',self.picking);

                    return new instance.web.Model('stock.move').call('read',[self.picking.move_lines, []]);
                }).then(function(movelines){
                    self.movelines = movelines;
                    console.log('Move Lines:',movelines);

                    return new instance.web.Model('stock.pack.operation').call('read',[self.picking.pack_operation_ids, []]);
                }).then(function(operations){
                    self.operations = operations;
                    console.log('Operations:',self.operations);
                    
                    var package_ids = [];

                    for(var i = 0; i < operations.length; i++){
                        if(!_.contains(package_ids,operations[i].result_package_id[0])){
                            package_ids.push(operations[i].result_package_id[0]);
                        }
                    }
                    console.log('Package ids:',package_ids);

                    return new instance.web.Model('stock.quant.package').call('read',[package_ids, []]);
                }).then(function(packages){
                    self.packages = packages;
                    console.log('Packages:', self.packages);
                });

            return loaded;
        },
        start: function(){
            var self = this;
            instance.webclient.set_content_full_screen(true);
            this.connect_barcode_scanner();

            this.$('.js_pick_quit').click(function(){ self.quit(); });
            this.$('.js_pick_pack').click(function(){ self.pack(); });
            this.$('.js_pick_done').click(function(){ self.done(); });

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
        // reloads the data from the provided picking and refresh the ui. 
        // (if no picking_id is provided, gets the first picking in the db)
        refresh_ui: function(picking_id){
            var self = this;
            return this.load(picking_id)
                .then(function(){ 
                    console.log('Refreshing UI');
                    self.picking_editor.renderElement();
                    self.package_editor.renderElement();
                    self.package_selector.renderElement();
                });
        },
        scan: function(ean){
            var self = this;
            console.log('Scan: ',ean);
            new instance.web.Model('stock.picking')
                .call('get_barcode_and_return_todo_stuff', [self.picking.id, ean])
                .then(function(){
                    return self.refresh_ui(self.picking.id);
                });
        },
        pack: function(){
            var self = this;
            console.log('Pack');
            new instance.web.Model('stock.picking')
                .call('action_pack',[[self.picking.id]])
                .then(function(){
                    instance.session.user_context.current_package_id = false;
                    console.log('Context Reset');

                    return self.refresh_ui(self.picking.id);
                });
        },
        done: function(){
            var self = this;
            console.log('Done');
            new instance.web.Model('stock.picking')
                .call('action_done_from_packing_ui',[[self.picking.id]])
                .then(function(new_picking_id){
                    console.log('New picking id:',new_picking_id);
                });
        },
        connect_barcode_scanner: function(){
            var self =this;
            var code = [];
            var timestamp = 0;
            $('body').delegate('','keyup',function(e){
                if (e.keyCode >= 48 && e.keyCode < 58){
                    if(timestamp + 30 < new Date().getTime()){
                        code = [];
                    }
                    timestamp = new Date().getTime();
                    code.push(e.keyCode - 48);
                    if(code.length === 13){
                        self.scan(code.join(''));
                        code = [];
                    }
                }else{
                    code = [];
                }
            });
        },
        disconnect_barcode_scanner: function(){
            $('body').undelegate('', 'keyup')
        },
        quit: function(){
            console.log('Quit');
            disconnect_barcode_scanner();
            instance.webclient.set_content_full_screen(false);
            window.location = '/'; // FIXME THIS IS SHIT NIV WILL KILL YOU (BY MULTIPLE FACE-STABBING) IF YOU MERGE THIS IN TRUNK
        },
    });
}
