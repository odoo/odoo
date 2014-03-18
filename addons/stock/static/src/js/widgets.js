
function openerp_picking_widgets(instance){

    var module = instance.stock;
    var _t     = instance.web._t;
    var QWeb   = instance.web.qweb;

    // This widget makes sure that the scaling is disabled on mobile devices.
    // Widgets that want to display fullscreen on mobile phone need to extend this
    // widget.

    module.MobileWidget = instance.web.Widget.extend({
        start: function(){
            if(!$('#oe-mobilewidget-viewport').length){
                $('head').append('<meta id="oe-mobilewidget-viewport" name="viewport" content="initial-scale=1.0; maximum-scale=1.0; user-scalable=0;">');
            }
            return this._super();
        },
        destroy: function(){
            $('#oe-mobilewidget-viewport').remove();
            return this._super();
        },
    });

    module.PickingEditorWidget = instance.web.Widget.extend({
        template: 'PickingEditorWidget',
        init: function(parent,options){
            this._super(parent,options);
            this.rows = [];
            this.search_filter = "";
        },
        get_rows: function(){
            var model = this.getParent();
            this.rows = [];
            var self = this;
            var pack_created = [];
            _.each( model.packoplines, function(packopline){
                    var pack = undefined;
                    if (packopline.product_id[1] !== undefined){ pack = packopline.package_id[1];}
                    //also check that we don't have a line already existing for that package
                    if (packopline.result_package_id[1] !== undefined && $.inArray(packopline.result_package_id[0], pack_created) === -1){
                        self.rows.push({
                            cols: { product: packopline.result_package_id[1],
                                    qty: '',
                                    rem: '',
                                    uom: undefined,
                                    lot: undefined,
                                    pack: undefined,
                                    container: packopline.result_package_id[1],
                                    container_id: undefined,
                                    loc: packopline.location_id[1],
                                    dest: packopline.location_dest_id[1],
                                    id: packopline.result_package_id[0],
                                    product_id: undefined,
                                    can_scan: false,
                                    head_container: true,
                                    processed: packopline.processed,
                            },
                            classes: ('active container_head ') + (packopline.processed === "true" ? 'processed hidden ':''),
                        });
                        pack_created.push(packopline.result_package_id[0]);
                    }
                    self.rows.push({
                        cols: { product: packopline.product_id[1] || packopline.package_id[1],
                                qty: packopline.product_qty,
                                rem: packopline.qty_done,
                                uom: packopline.product_uom_id[1],
                                lot: packopline.lot_id[1],
                                pack: pack,
                                container: packopline.result_package_id[1],
                                container_id: packopline.result_package_id[0],
                                loc: packopline.location_id[1],
                                dest: packopline.location_dest_id[1],
                                id: packopline.id,
                                product_id: packopline.product_id[0],
                                can_scan: packopline.result_package_id[1] === undefined ? true : false,
                                head_container: false,
                                processed: packopline.processed,
                        },
                        classes: ((packopline.product_qty <= packopline.qty_done) ? 'active ' : '') + (packopline.result_package_id[1] !== undefined ? 'in_container_hidden ' : '') + (packopline.processed === "true" ? 'processed hidden ':''),
                    });
            });
            //sort element by things to do, then things done, then grouped by packages
            group_by_container = _.groupBy(self.rows, function(row){
                return row.cols.container;
            });
            var sorted_row = [];
            if (group_by_container.undefined !== undefined){
                group_by_container.undefined.sort(function(a,b){return (b.classes === '') - (a.classes === '');});
                $.each(group_by_container.undefined, function(key, value){
                    sorted_row.push(value);
                });
            }

            $.each(group_by_container, function(key, value){
                if (key !== 'undefined'){
                    $.each(value, function(k,v){
                        sorted_row.push(v);
                    });
                }
            });

            return sorted_row;
        },
        renderElement: function(){
            var self = this;
            this._super();
            this.$('#js_select').change(function(){
                var selection = $(this)[0].value
                if (selection === "ToDo"){
                    self.getParent().$('.js_pick_pack').removeClass('hidden')
                    self.getParent().$('.js_drop_down').removeClass('hidden')
                    self.$('.js_pack_op_line.processed').addClass('hidden')
                    self.$('.js_pack_op_line:not(.processed)').removeClass('hidden')
                }
                else{
                    self.getParent().$('.js_pick_pack').addClass('hidden')
                    self.getParent().$('.js_drop_down').addClass('hidden')
                    self.$('.js_pack_op_line.processed').removeClass('hidden')
                    self.$('.js_pack_op_line:not(.processed)').addClass('hidden')
                }
                self.on_searchbox(self.search_filter);
            });
            this.$('.js_plus').click(function(){
                var id = parseInt($(this).attr('op-id'));
                self.getParent().scan_product_id(id,true);
            });
            this.$('.js_minus').click(function(){
                var id = parseInt($(this).attr('op-id'));
                self.getParent().scan_product_id(id,false);
            });
            this.$('.js_unfold').click(function(){
                var op_id = $(this).parent()[0].attributes.getNamedItem('data-id').value;
                var line = $(this).parent();
                //select all js_pack_op_line with class in_container_hidden and correct container-id
                select = self.$('.js_pack_op_line.in_container_hidden[container-id='+op_id+']')
                if (select.length > 0){
                    //we unfold
                    line.addClass('warning');
                    select.removeClass('in_container_hidden');
                    select.addClass('in_container'); 
                }
                else{
                    //we fold
                    line.removeClass('warning');
                    select = self.$('.js_pack_op_line.in_container[container-id='+op_id+']')
                    select.removeClass('in_container');
                    select.addClass('in_container_hidden'); 
                }
            });
            this.$('.js_create_lot').click(function(){
                var op_id = this.attributes.getNamedItem('product_id').value;
                self.getParent().create_lot(op_id);
            });
            this.$('.js_delete_pack').click(function(){
                var pack_id = parseInt(this.attributes.getNamedItem('pack_id').value);
                self.getParent().delete_package_op(pack_id);
            });
            this.$('.js_print_pack').click(function(){
                var pack_id = parseInt(this.attributes.getNamedItem('pack_id').value);
                self.getParent().print_package(pack_id);
            });
            this.$('.js_pick_drop_down').click(function(){
                //check if parent is a container, if yes find all operation inside package
                var op_id = parseInt($(this).parent().parent().parent().parent().parent().attr('data-id'));
                if ($(this).parent().parent().parent().parent().parent()[0].classList.contains('container_head')){
                    op_ids = []
                    _.each(self.$('.js_pack_op_line[container-id='+op_id+']'),function(element){
                        op_ids.push(parseInt(element.attributes.getNamedItem('data-id').value));
                    });
                    self.getParent().drop_down(op_ids);
                }
                else{
                    self.getParent().drop_down([op_id]);
                }
                
            });
            this.$('.js_submit_value').submit(function(event){
                var op_id = parseInt(this.attributes.getNamedItem('data-id').value);
                var value = parseInt(event.srcElement[0].value);
                if (value>=0){
                    self.getParent().set_operation_quantity(value, op_id);
                }
                self.$('.js_qty[data-id='+op_id+']')[0].value = "";
            });
            this.$('.js_qty').blur(function(){
                this.value = "";
            })
            //remove navigtion bar from default openerp GUI
            $('td.navbar').html('<div></div>');
        },
        on_searchbox: function(query){
            //hide line that has no location matching the query and highlight location that match the query
            this.search_filter = query;
            var processed = ".processed";
            if (this.$('#js_select')[0].value == "ToDo"){
                processed = ":not(.processed)";
            }
            if (query !== '') {
                this.$('.js_loc:not(.js_loc:contains('+query+'))').removeClass('info');
                this.$('.js_loc:contains('+query+')').addClass('info');
                this.$('.js_pack_op_line'+processed+':not(.js_pack_op_line:has(.js_loc:contains('+query+')))').addClass('hidden');
                this.$('.js_pack_op_line'+processed+':has(.js_loc:contains('+query+'))').removeClass('hidden');
            }
            //if no query specified, then show everything
            if (query === '') {
                this.$('.js_loc').removeClass('info');
                this.$('.js_pack_op_line'+processed+'.hidden').removeClass('hidden');
            }
        },
        get_current_op_selection: function(ignore_container){
            //get ids of visible on the screen
            pack_op_ids = []
            this.$('.js_pack_op_line:not(.processed):not(.js_pack_op_line.hidden):not(.container_head)').each(function(){
                cur_id = this.attributes.getNamedItem('data-id').value;
                pack_op_ids.push(parseInt(cur_id));
            });
            //get list of element in this.rows where rem > 0 and container is empty is specified
            list = []
            _.each(this.rows, function(row){
                if (row.cols.rem > 0 && (ignore_container || row.cols.container === undefined)){
                    list.push(row.cols.id);
                }
            });
            //return only those visible with rem qty > 0 and container empty
            return _.intersection(pack_op_ids, list);
        },
    });

    module.PickingMenuWidget = module.MobileWidget.extend({
        template: 'PickingMenuWidget',
        init: function(parent, params){
            this._super(parent,params);
            var self = this;

            this.picking_types = [];
            this.loaded = this.load();
            this.scanning_type = 0;
            this.barcode_scanner = new module.BarcodeScanner();
            this.pickings_by_type = {};
            this.pickings_by_id = {};
            this.picking_search_string = "";
        },
        load: function(){
            var self = this;
            return new instance.web.Model('stock.picking.type').get_func('search_read')([],[])
                .then(function(types){
                    self.picking_types = types;
                    for(var i = 0; i < types.length; i++){
                        self.pickings_by_type[types[i].id] = [];
                    }
                    self.pickings_by_type[0] = [];

                    return new instance.web.Model('stock.picking').call('search_read',[ [['state','in', ['assigned', 'partially_available']]], [] ], {context: new instance.web.CompoundContext()});
                                                                  
                }).then(function(pickings){
                    self.pickings = pickings;
                    for(var i = 0; i < pickings.length; i++){
                        var picking = pickings[i];
                        self.pickings_by_type[picking.picking_type_id[0]].push(picking);
                        self.pickings_by_id[picking.id] = picking;
                        self.picking_search_string += '' + picking.id + ':' + picking.name.toUpperCase() + '\n'
                    }

                });
        },
        renderElement: function(){
            this._super();
            var self = this;
            this.$('.js_pick_quit').click(function(){ self.quit(); });
            this.$('.js_pick_scan').click(function(){ self.scan_picking($(this).data('id')); });
            this.$('.js_pick_last').click(function(){ self.goto_last_picking_of_type($(this).data('id')); });
            this.$('.oe_searchbox').keyup(function(event){
                self.on_searchbox($(this).val());
            });
            //remove navigtion bar from default openerp GUI
            $('td.navbar').html('<div></div>');
        },
        start: function(){
            this._super();
            var self = this;
            instance.webclient.set_content_full_screen(true);
            this.barcode_scanner.connect(function(barcode){
                self.on_scan(barcode);
            });
            this.loaded.then(function(){
                self.renderElement();
            });
        },
        goto_picking: function(picking_id){
            this.do_action({
                type:   'ir.actions.client',
                tag:    'stock.ui',
                target: 'current',
                context: { picking_id: picking_id },
            },{
                clear_breadcrumbs: true,
            });
        },
        goto_last_picking_of_type: function(type_id){
            this.do_action({
                type:   'ir.actions.client',
                tag:    'stock.ui',
                target: 'current',
                context: { active_id: type_id },
            },{
                clear_breadcrumbs: true,
            });
        },
        search_picking: function(barcode){
            //TODO don't crash if a not supported char is given
            var re = RegExp("([0-9]+):.*?"+barcode.toUpperCase(),"gi");
            var results = [];
            for(var i = 0; i < 100; i++){
                r = re.exec(this.picking_search_string);
                if(r){
                    var picking = this.pickings_by_id[Number(r[1])];
                    if(picking){
                        results.push(picking);
                    }
                }else{
                    break;
                }
            }
            return results;
        },
        on_scan: function(barcode){
            var self = this;
            for(var i = 0, len = this.pickings.length; i < len; i++){
                var picking = this.pickings[i];
                if(picking.name.toUpperCase() === $.trim(barcode.toUpperCase())){
                    this.goto_picking(picking.id);
                    break;
                }
            }
            this.$('.js_picking_not_found').removeClass('hidden');

            clearTimeout(this.picking_not_found_timeout);
            this.picking_not_found_timeout = setTimeout(function(){
                self.$('.js_picking_not_found').addClass('hidden');
            },2000);

        },
        on_searchbox: function(query){
            var self = this;

            clearTimeout(this.searchbox_timeout);
            this.searchbox_timout = setTimeout(function(){
                if(query){
                    self.$('.js_picking_not_found').addClass('hidden');
                    self.$('.js_picking_categories').addClass('hidden');
                    self.$('.js_picking_search_results').html(
                        QWeb.render('PickingSearchResults',{results:self.search_picking(query)})
                    );
                    self.$('.js_picking_search_results .oe_picking').click(function(){
                        self.goto_picking($(this).data('id'));
                    });
                    self.$('.js_picking_search_results').removeClass('hidden');
                }else{
                    self.$('.js_title_label').removeClass('hidden');
                    self.$('.js_picking_categories').removeClass('hidden');
                    self.$('.js_picking_search_results').addClass('hidden');
                }
            },100);
        },
        quit: function(){
            return new instance.web.Model("ir.model.data").get_func("search_read")([['name', '=', 'action_picking_type_form']], ['res_id']).pipe(function(res) {
                    window.location = '/web#action=' + res[0]['res_id'];
                });
        },
        destroy: function(){
            this._super();
            this.barcode_scanner.disconnect();
            instance.webclient.set_content_full_screen(false);
        },
    });
    openerp.web.client_actions.add('stock.menu', 'instance.stock.PickingMenuWidget');

    module.PickingMainWidget = module.MobileWidget.extend({
        template: 'PickingMainWidget',
        init: function(parent,params){
            $(window).bind('hashchange', function(){
                console.log($.bbq.getState());
                console.log('test');
            });
            this._super(parent,params);
            var self = this;

            this.picking = null;
            this.pickings = [];
            this.packoplines = null;
            this.operations = null;
            this.selected_operation = { id: null, picking_id: null};
            this.packages = null;
            this.barcode_scanner = new module.BarcodeScanner();
            this.picking_type_id = params.context.active_id || 0;

            if(params.context.picking_id){
                this.loaded =  this.load(params.context.picking_id);
            }else{
                this.loaded =  this.load();
            }

        },

        // load the picking data from the server. If picking_id is undefined, it will take the first picking
        // belonging to the category
        load: function(picking_id){
            var self = this;

       
            function load_picking_list(type_id){
                var pickings = new $.Deferred();
                new instance.web.Model('stock.picking')
                    .call('get_next_picking_for_ui',[{'default_picking_type_id':type_id}])
                    .then(function(picking_ids){
                        if(!picking_ids || picking_ids.length === 0){
                            (new instance.web.Dialog(self,{
                                title: _t('No Picking Available'),
                                buttons: [{ 
                                    text:_t('Ok'), 
                                    click: function(){
                                        self.menu();
                                    }
                                }]
                            }, _t('<p>We could not find a picking to display.</p>'))).open();

                            pickings.reject();
                        }else{
                            self.pickings = picking_ids;
                            pickings.resolve(picking_ids);
                        }
                    });

                return pickings;
            }

            // if we have a specified picking id, we load that one, and we load the picking of the same type as the active list
            if( picking_id ){
                var loaded_picking = new instance.web.Model('stock.picking')
                    .call('read',[[picking_id], [], new instance.web.CompoundContext()])
                    .then(function(picking){
                        self.picking = picking[0];

                        return load_picking_list(self.picking.picking_type_id[0]);
                    });
            }else{
                // if we don't have a specified picking id, we load the pickings belong to the specified type, and then we take 
                // the first one of that list as the active picking
                var loaded_picking = new $.Deferred();
                load_picking_list(self.picking_type_id)
                    .then(function(){
                        return new instance.web.Model('stock.picking').call('read',[self.pickings[0],[], new instance.web.CompoundContext()]);
                    })
                    .then(function(picking){
                        self.picking = picking;
                        self.picking_type_id = picking.picking_type_id[0];
                        loaded_picking.resolve();
                    });
            }

            return loaded_picking.then(function(){

                    return new instance.web.Model('stock.pack.operation').call('read',[self.picking.pack_operation_ids, [], new instance.web.CompoundContext()]);
                }).then(function(packoplines){
                    self.packoplines = packoplines;

                    return new instance.web.Model('stock.pack.operation').call('read',[self.picking.pack_operation_ids, [], new instance.web.CompoundContext()]);
                }).then(function(operations){
                    self.operations = operations;
                    var package_ids = [];

                    for(var i = 0; i < operations.length; i++){
                        if(!_.contains(package_ids,operations[i].result_package_id[0])){
                            if (operations[i].result_package_id[0]){
                                package_ids.push(operations[i].result_package_id[0]);
                            }
                        }
                    }
                    return new instance.web.Model('stock.quant.package').call('read',[package_ids, [], new instance.web.CompoundContext()]);
                }).then(function(packages){
                    self.packages = packages;
                });

        },
        start: function(){
            this._super();
            var self = this;
            instance.webclient.set_content_full_screen(true);
            this.barcode_scanner.connect(function(ean){
                self.scan(ean);
            });
            

            this.$('.js_pick_quit').click(function(){ self.quit(); });
            this.$('.js_pick_pack').click(function(){ self.pack(); });
            this.$('.js_drop_down').click(function(){ self.drop_down();});
            this.$('.js_pick_done').click(function(){ self.done(); });
            this.$('.js_pick_print').click(function(){ self.print_picking(); });
            this.$('.js_pick_prev').click(function(){ self.picking_prev(); });
            this.$('.js_pick_next').click(function(){ self.picking_next(); });
            this.$('.js_pick_menu').click(function(){ self.menu(); });
            this.$('.oe_searchbox').keyup(function(event){
                self.on_searchbox($(this).val());
            });
            this.$('.js_clear_search').click(function(){ 
                self.on_searchbox(''); 
                self.$('.oe_searchbox').val('');
            });

            this.hotkey_handler = function(event){
                if(event.keyCode === 37 ){  // Left Arrow
                    self.picking_prev();
                }else if(event.keyCode === 39){ // Right Arrow
                    self.picking_next();
                }
            };

            $('body').on('keyup',this.hotkey_handler);

            $.when(this.loaded).done(function(){
                self.picking_editor = new module.PickingEditorWidget(self);
                self.picking_editor.replace(self.$('.oe_placeholder_picking_editor'));
                
                if( self.picking.id === self.pickings[0]){
                    self.$('.js_pick_prev').addClass('disabled');
                }else{
                    self.$('.js_pick_prev').removeClass('disabled');
                }
                
                if( self.picking.id === self.pickings[self.pickings.length-1] ){
                    self.$('.js_pick_next').addClass('disabled');
                }else{
                    self.$('.js_pick_next').removeClass('disabled');
                }

                self.$('.oe_pick_app_header').text(self.get_header());

            }).fail(function(error) {console.log(error);});

        },
        on_searchbox: function(query){
            var self = this;
            self.picking_editor.on_searchbox(query);
        },
        // reloads the data from the provided picking and refresh the ui. 
        // (if no picking_id is provided, gets the first picking in the db)
        refresh_ui: function(picking_id){
            var self = this;
            var remove_search_filter = true;
            if (self.picking.id === picking_id){
                remove_search_filter = false;
            }
            return this.load(picking_id)
                .then(function(){
                    self.picking_editor.renderElement();
                    // self.$('#js_select')[0].value = "ToDo";

                    if( self.picking.id === self.pickings[0]){
                        self.$('.js_pick_prev').addClass('disabled');
                    }else{
                        self.$('.js_pick_prev').removeClass('disabled');
                    }
                    
                    if( self.picking.id === self.pickings[self.pickings.length-1] ){
                        self.$('.js_pick_next').addClass('disabled');
                    }else{
                        self.$('.js_pick_next').removeClass('disabled');
                    }
                    self.$('.oe_pick_app_header').text(self.get_header());
                    if (remove_search_filter){
                        self.$('.oe_searchbox').val('');
                        self.on_searchbox('');
                    }
                    else{
                        self.on_searchbox(self.$('.oe_searchbox').val());
                    }
                });
        },
        get_header: function(){
            if(this.picking){
                return this.picking.name;
            }else{
                return '';
            }
        },
        menu: function(){
            this.do_action({
                type:   'ir.actions.client',
                tag:    'stock.menu',
                target: 'current',
            },{
                clear_breadcrumbs: true,
            });

        },
        scan: function(ean){ //scans a barcode, sends it to the server, then reload the ui
            var self = this;
            new instance.web.Model('stock.picking')
                .call('process_barcode_from_ui', [self.picking.id, ean])
                .then(function(result){
                    if (result.filter_loc !== false){
                        //check if we have receive a location as answer
                        if (result.filter_loc !== undefined){
                            self.$('.oe_searchbox').val(result.filter_loc);
                            self.on_searchbox(result.filter_loc);
                        }
                    }
                    console.log(result.operation_id);
                    if (result.operation_id !== false){
                        return self.refresh_ui(self.picking.id);
                    }
                });
        },
        scan_product_id: function(product_id,increment){ //performs the same operation as a scan, but with product id instead
            var self = this;
            new instance.web.Model('stock.picking')
                .call('process_product_id_from_ui', [self.picking.id, product_id, increment])
                .then(function(result){
                    return self.refresh_ui(self.picking.id);
                });
        },
        pack: function(){
            var self = this;
            var pack_op_ids = self.picking_editor.get_current_op_selection(false);
            if (pack_op_ids.length !== 0){
                new instance.web.Model('stock.picking')
                    .call('action_pack',[[[self.picking.id]], pack_op_ids])
                    .then(function(){
                        instance.session.user_context.current_package_id = false;
                        return self.refresh_ui(self.picking.id);
                    });
            }
        },
        drop_down: function(){
            var self = this;
            var pack_op_ids = self.picking_editor.get_current_op_selection(true);
            if (pack_op_ids.length !== 0){
                new instance.web.Model('stock.pack.operation')
                    .call('action_drop_down', [pack_op_ids])
                    .then(function(){
                        return self.refresh_ui(self.picking.id);
                    });
            }
        },
        done: function(){
            var self = this;
            new instance.web.Model('stock.picking')
                .call('action_done_from_ui',[self.picking.id, {'default_picking_type_id': self.picking_type_id}])
                .then(function(new_picking_ids){
                    if (new_picking_ids){
                        return self.refresh_ui(new_picking_ids[0]);
                    }
                    else {
                        return 0;
                    }
                });
        },
        create_lot: function(op_id){
            var self = this;
            new instance.web.Model('stock.pack.operation')
                .call('create_and_assign_lot',[parseInt(op_id)])
                .then(function(){
                    return self.refresh_ui(self.picking.id);
                });
        },
        print_package: function(package_id){
            var self = this;
            new instance.web.Model('stock.quant.package')
                .call('action_print',[[package_id]])
                .then(function(action){
                    return self.do_action(action);
                });
        },
        print_picking: function(){
            var self = this;
            new instance.web.Model('stock.picking.type').call('read', [[self.picking_type_id], ['code'], new instance.web.CompoundContext()])
                .then(function(pick_type){
                    if (pick_type[0]['code'] == 'outgoing'){
                        new instance.web.Model('stock.picking').call('do_print_delivery',[[self.picking.id]])
                           .then(function(action){
                                return self.do_action(action);
                           });
                    }
                    else {
                        new instance.web.Model('stock.picking').call('do_print_picking',[[self.picking.id]])
                           .then(function(action){
                                return self.do_action(action);
                           });
                    }
                });
        },
        do_load_state: function(){
            debugger;
        },
        picking_next: function(){
            for(var i = 0; i < this.pickings.length; i++){
                if(this.pickings[i] === this.picking.id){
                    if(i < this.pickings.length -1){
                        window.location = '/barcode/web/?picking_type_id='+this.picking_type_id+'&picking_id='+this.pickings[i+1];
                        return;
                        // this.refresh_ui(this.pickings[i+1]);
                        // return;
                    }
                }
            }
        },
        picking_prev: function(){
            for(var i = 0; i < this.pickings.length; i++){
                if(this.pickings[i] === this.picking.id){
                    if(i > 0){
                        window.location = '/barcode/web/?picking_type_id='+this.picking_type_id+'&picking_id='+this.pickings[i-1];
                        // this.refresh_ui(this.pickings[i-1]);
                        return;
                    }
                }
            }
        },
        delete_package_op: function(pack_id){
            var self = this;
            new instance.web.Model('stock.pack.operation').call('search', [[['result_package_id', '=', pack_id]]])
                .then(function(op_ids) {
                    new instance.web.Model('stock.pack.operation').call('write', [op_ids, {'result_package_id':false}])
                        .then(function() {
                            return self.refresh_ui(self.picking.id);
                        });
                });
        },
        set_operation_quantity: function(quantity, op_id){
            var self = this;
            if(quantity >= 0){
                new instance.web.Model('stock.pack.operation')
                    .call('write',[[op_id],{'qty_done': quantity }])
                    .then(function(){
                        self.refresh_ui(self.picking.id);
                    });
            }

        },
        quit: function(){
            this.destroy();
            return new instance.web.Model("ir.model.data").get_func("search_read")([['name', '=', 'action_picking_type_form']], ['res_id']).pipe(function(res) {
                    window.location = '/web#action=' + res[0]['res_id'];
                });
        },
        destroy: function(){
            this._super();
            // this.disconnect_numpad();
            this.barcode_scanner.disconnect();
            $('body').off('keyup',this.hotkey_handler);
            instance.webclient.set_content_full_screen(false);
        },
    });
    openerp.web.client_actions.add('stock.ui', 'instance.stock.PickingMainWidget');

    module.BarcodeScanner = instance.web.Class.extend({
        connect: function(callback){
            var code = "";
            var timeStamp = 0;
            var timeout = null;

            this.handler = function(e){
                if(e.which === 13){ //ignore returns
                    return;
                }

                if(timeStamp + 50 < new Date().getTime()){
                    code = "";
                }

                timeStamp = new Date().getTime();
                clearTimeout(timeout);

                code += String.fromCharCode(e.which);

                timeout = setTimeout(function(){
                    if(code.length >= 3){
                        callback(code);
                    }
                    code = "";
                },100);
            };

            $('body').on('keypress', this.handler);

        },
        disconnect: function(){
            $('body').off('keypress', this.handler);
        },
    });

}

openerp.stock = function(openerp) {
    openerp.stock = openerp.stock || {};
    openerp_picking_widgets(openerp);
}