
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
            var current_package = model.get_selected_package();
            return current_package ? 'Operations for Package: ' + current_package.name : 'Current Operations';
        },
        get_rows: function(){
            var model = this.getParent();
            var rows = [];
            var current_package_id = instance.session.user_context.current_package_id;
            _.each( model.operations, function(op){
		if (!current_package_id){
			if (op.result_package_id !== false){
				return;
			}
		} else if(op.result_package_id[0] !== current_package_id){
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
            var current_package = model.get_selected_package();
            var rows = [];
            _.each( model.packages, function(pack){
                rows.push({
                    cols:{ pack: pack.name},
                    id: pack.id,
                    classes: pack === current_package ? ' oe_selected' : '' ,
                });
            });
            return rows;
        },
        renderElement: function(){
            this._super();
            var model = this.getParent();
            this.$('.js_pack_row').each(function(){
                var pack_id = parseInt($(this).attr('pack-id'));

                $('.js_pack_plus', this).click(function(){ model.copy_package(pack_id); });
                $('.js_pack_minus', this).click(function(){ model.delete_package(pack_id); });
                $('.js_pack_select', this).click(function(){ 
                    if(model.get_selected_package() && model.get_selected_package().id === pack_id){
                        model.deselect_package();
                    }else{
                        model.select_package(pack_id); 
                    }
                });
            });
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
            this.scan_timestamp = 0;
            
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
                    console.log('User Context:', instance.session.user_context);
                    console.log('Context:', new instance.web.CompoundContext().eval());

                    return new instance.web.Model('stock.move').call('read',[self.picking.move_lines, [], new instance.web.CompoundContext()]);
                }).then(function(movelines){
                    self.movelines = movelines;
                    console.log('Move Lines:',movelines);

                    return new instance.web.Model('stock.pack.operation').call('read',[self.picking.pack_operation_ids, [], new instance.web.CompoundContext()]);
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

                    return new instance.web.Model('stock.quant.package').call('read',[package_ids, [], new instance.web.CompoundContext()]);
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
            this.scan_timestamp = new Date().getTime();
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
                    //return self.refresh_ui(new_picking_id);
                });
        },
        copy_package: function(package_id){
            var self = this;
            console.log('Copy Package:',package_id);
            new instance.web.Model('stock.quant.package')
                .call('action_copy',[[package_id]])
                .then(function(){
                    return self.refresh_ui(self.picking.id);
                });
        },
        delete_package: function(package_id){
            var self = this;
            console.log('Delete Package:',package_id);
            new instance.web.Model('stock.quant.package')
                .call('unlink',[[package_id]])
                .then(function(){
                    return self.refresh_ui(self.picking.id);
                });
        },
        deselect_package: function(){
            console.log('Deselect Package');
            instance.session.user_context.current_package_id = false;
            this.package_editor.renderElement();
            this.package_selector.renderElement();
        },
        select_package: function(package_id){
            console.log('Select Package:',package_id);
            instance.session.user_context.current_package_id = package_id;
            this.package_editor.renderElement();
            this.package_selector.renderElement();
        },
        get_selected_package: function(){
            var current_package;

            _.each( this.packages, function(pack){
                if(pack.id === instance.session.user_context.current_package_id){
                    current_package = pack;
                }
            });

            return current_package;
        },
        connect_barcode_scanner: function(){
            var self =this;
            var numbers = [];
            var timestamp = 0;
            var nocode_timeout_id = 0;
            var nocode_delay = 50;
            function nocode(){
                //console.log('NoCode:',numbers);
                numbers = [];
            }
            // it is important to catch the keypress event and not keyup/keydown as keypress normalizes the input codes :) 
            $('body').delegate('','keypress',function(e){ 
                //console.log('Key:',e);
                if (e.keyCode >= 48 && e.keyCode < 58){
                    clearTimeout(nocode_timeout_id);
                    nocode_timeout_id = setTimeout(nocode,nocode_delay);
                    if(timestamp + 30 < new Date().getTime()){
                        clearTimeout(nocode_timeout_id);
                        nocode();
                    }
                    numbers.push(e.keyCode - 48);
                    timestamp = new Date().getTime();
                    if(numbers.length === 13){
                        self.scan(numbers.join(''));
                        numbers = [];
                        clearTimeout(nocode_timeout_id);
                    }
                }else{
                    nocode();
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
