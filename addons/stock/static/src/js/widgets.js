
function openerp_picking_widgets(instance){
    var module = instance.stock;
    var _t = instance.web._t;

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
                            qty: moveline.product_uom_qty,
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
            var ops = model.get_current_operations();

            _.each( ops, function(op){
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

                $('.js_pack_print', this).click(function(){ model.print_package(pack_id); });
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
            this.numpad_buffer  = [];
            
            window.pickwidget = this;
            
            console.log('Action params:', params);
            console.log('Session:',instance.session);

            this.loaded =  this.load();
        },
        load: function(picking_id){
            var self = this;

            console.log('LOADING DATA FROM SERVER');

            if(picking_id){
                var picking = new instance.web.Model('stock.picking').call('read',[[picking_id], []]);
            }else{ 
                var picking = new instance.web.Model('stock.picking')
                    .call('get_picking_for_packing_ui')
                    .then(function(picking_id){
                        if(!picking_id){
                            (new instance.web.Dialog(self,{
                                title: _t('No Picking Available'),
                                buttons: [{ 
                                    text:_t('Ok'), 
                                    click: function(){
                                        self.quit();
                                    }
                                }]
                            }, _t('<p>We could not find a picking to display.</p>'))).open();

                            return (new $.Deferred()).reject();
                        }else{
                            return new instance.web.Model('stock.picking').call('read',[[picking_id],[]]);
                        }
                    });
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
            this.connect_barcode_scanner_and_numpad();

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
                    console.log('REFRESHING UI');
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
                .call('action_pack',[[[self.picking.id]]])
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
                .call('action_done_from_packing_ui',[self.picking.id])
                .then(function(new_picking_id){
                    console.log('New picking id:',new_picking_id);
                    return self.refresh_ui(new_picking_id);
                });
        },
        print_package: function(package_id){
            var self = this;
            console.log('Print Package:',package_id);
            new instance.web.Model('stock.quant.package')
                .call('action_print',[[package_id]])
                .then(function(action){
                    console.log('Print Package Repport Action:',action);
                    return self.do_action(action);
                });
        },
        copy_package: function(package_id){
            var self = this;
            console.log('Copy Package:',package_id);
            new instance.web.Model('stock.quant.package')
                .call('copy',[[package_id]])
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
        get_current_operations: function(){
            var current_package_id = instance.session.user_context.current_package_id;
            var ops = [];
            _.each( this.operations, function(op){
                if(!current_package_id){
                    if(op.result_package_id !== false){
                        return;
                    }
                }else if(op.result_package_id[0] !== current_package_id){
                    return;
                }
                ops.push(op);
            });
            return ops;
        },
        set_operation_quantity: function(quantity){
            var self = this;
            var ops = this.get_current_operations();
            if( !ops || ops.length === 0){
                return;
            }
            var op = ops[ops.length-1];

            if(quantity === '++'){
                console.log('Increase quantity!');
                quantity = op.product_qty + 1;
            }else if(quantity === '--'){
                console.log('Decrease quantity :(');
                quantity = op.product_qty - 1;
            }

            if(typeof quantity === 'number' && quantity >= 0){
                console.log('Set quantity: ',quantity);
                new instance.web.Model('stock.pack.operation')
                    .call('write',[[op.id],{'product_qty': quantity }])
                    .then(function(){
                        self.refresh_ui(self.picking.id);
                    });
            }

        },
        connect_barcode_scanner_and_numpad: function(){
            var self = this;
            var numbers = [];
            var timestamp = 0;
            var numpad = [];
            var numpad_timestamp;
            // it is important to catch the keypress event and not keyup/keydown as keypress normalizes the input codes :) 
            $('body').delegate('','keyup',function(e){ 
                //console.log('Key:',e.keyCode);
                if (e.keyCode >= 48 && e.keyCode < 58){
                    if(timestamp + 30 < new Date().getTime()){
                        numbers = [];
                    }
                    numbers.push(e.keyCode - 48);
                    timestamp = new Date().getTime();
                    if(numbers.length === 13){
                        self.scan(numbers.join(''));
                        numbers = [];
                    }
                }else{
                    numbers = [];
                    if(numpad_timestamp + 1500 < new Date().getTime()){
                        numpad = [];
                    }
                    if(e.keyCode === 27 || e.keyCode === 8){ // ESC or BACKSPACE
                        numpad = [];
                    }else if(e.keyCode >= 96 && e.keyCode <= 105){ // NUMPAD NUMBERS
                        numpad.push(e.keyCode - 96);
                    }else if(e.keyCode === 13){ // ENTER
                        if(numpad.length > 0){
                            self.set_operation_quantity(parseInt(numpad.join('')));
                        }
                        numpad = [];
                    }else if(e.keyCode === 107){ // NUMPAD +
                        self.set_operation_quantity('++');
                        numpad = [];
                    }else if(e.keyCode === 109){ // NUMPAD -
                        self.set_operation_quantity('--');
                        numpad = [];
                    }else{
                        numpad = [];
                    }
                    numpad_timestamp = new Date().getTime();
                }
            });
        },
        disconnect_barcode_scanner_and_numpad: function(){
            $('body').undelegate('', 'keyup')
        },
        quit: function(){
            console.log('Quit');
            this.disconnect_barcode_scanner_and_numpad();
            instance.webclient.set_content_full_screen(false);
            window.location = '/'; // FIXME Ask niv how to do it correctly
        },
    });
}
