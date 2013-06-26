
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
            return this._rows || [
                { cols: { product:'abc', qty:1, rem: 4, uom: 5, loc: 'def', stat: 'available' },   },
                { cols: { product:'dec', qty:2, rem: 3, uom: 5, loc: 'rcd', stat: 'available' },  classes: '' },
                { cols: { product:'qcr', qty:4, rem: 4, uom: 5, loc: 'hre', stat: 'unavailable' }, },
            ];
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
            
            console.log('Action params:', params);

            new instance.web.Model('stock.picking.in')
                .query()
                .all()
                .then(function(results){
                    console.log('Picking In:',results);
                });

            new instance.web.Model('stock.picking.out')
                .query()
                .all()
                .then(function(results){
                    console.log('Picking Out:',results);
                });

            new instance.web.Model('stock.quant.package')
                .query(['name','packaging_id','quant_ids','parent_id','children_ids','location_id','pack_operation_id'])
                .all()
                .then(function(result){
                    console.log('Packages: ',result);
                 });

            new instance.web.Model('stock.pack.operation')
                .query(['picking_id','product_id','product_uom','product_qty','package_id','quant_id','result_package_id'])
                .all()
                .then(function(results){
                    console.log('Pack Operations:',results);
                });

        },
        start: function(){
            var self = this;
            instance.webclient.set_content_full_screen(true);

            var picking_editor = new module.PickingEditorWidget(this);
            picking_editor.replace(this.$('.oe_placeholder_picking_editor'));

            var package_editor = new module.PackageEditorWidget(this);
            package_editor.replace(this.$('.oe_placeholder_package_editor'));

            var package_selector = new module.PackageSelectorWidget(this);
            package_selector.replace(this.$('.oe_placeholder_package_selector'));

            return this._super();
        },
    });
}
