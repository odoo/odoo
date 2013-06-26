
function openerp_picking_widgets(instance){
    var module = instance.stock;

    module.PickingEditorWidget = instance.web.Widget.extend({
        template: 'PickingEditorWidget',
        init: function(parent,options){
            this._super(parent,options);
        },
        get_header: function(){
            return this._header || 'Picking: INTERNAL/00112';
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
                            rem: moveline.qty_remaining,
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
            return this._rows || [
                { cols: { product:'abc', qty:1, uom: 5, },   },
                { cols: { product:'dec', qty:2, uom: 5, },  classes: '' },
                { cols: { product:'qcr', qty:4, uom: 5, }, },
            ];
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
                });

        },
        start: function(){
            var self = this;
            instance.webclient.set_content_full_screen(true);

            this.$('.js_pick_quit').click(function(){ self.quit(); });

            $.when(this.loaded).done(function(){
                var picking_editor = new module.PickingEditorWidget(self);
                picking_editor.replace(self.$('.oe_placeholder_picking_editor'));

                var package_editor = new module.PackageEditorWidget(self);
                package_editor.replace(self.$('.oe_placeholder_package_editor'));

                var package_selector = new module.PackageSelectorWidget(self);
                package_selector.replace(self.$('.oe_placeholder_package_selector'));
            });


            return this._super();
        },
        scan: function(ean){
            new instance.web.Model('stock.picking')
                .call('get_barcode_and_return_todo_stuff', [this.picking.id, ean])
                .then(function(results){
                    console.log('STUFF TODO:', arguments);
                });
        },
        quit: function(){
            console.log('Quit');
            instance.webclient.set_content_full_screen(false);
            window.location = '/'; // FIXME THIS IS SHIT NIV WILL KILL YOU (BY MULTIPLE FACE-STABBING) IF YOU MERGE THIS IN TRUNK
        },
    });
}
