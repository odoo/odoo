
function openerp_picking_widgets(instance){
    var module = instance.stock;

    /*
     * new TactileListWidget(parent,{
     *   height: '500px',
     *   width:  '100%',
     *   title:  'Sample List',
     *   collumns: [
     *      {header:'Foobar', classes:'oe_small'},
     *      {header:'Foobar', classes:'oe_medium'},
     *      {header:''      , classes:'oe_big'},
     *      {header:'BarFoo', classes:'oe_expand'},
     *   ],
     *   rows: [
     *      {cols: [0,1,2,3] },
     *      {cols: [1,2,3,4], classes:'oe_selected oe_invalid'},
     *      {cols: [2,1,3,4] },
     *   ]
     * });
     */

    module.TactileListWidget = instance.web.Widget.extend({
        template: 'TactileListWidget',
        init: function(parent, options){
            this._super(parent,options);
            this._collumns = options.collumns || [];
            this._rows = options.rows || [];
            this._title = options.title || '';
            this._width = options.width || 625;
            this._height = options.height || 200;
            this._scrollbarwidth = 15;
        },
        renderElement: function(){
            var self = this;
            this._super();
            this.$('.js_vresizer, .js_hresizer').mousedown(function(event){
                self._startsize = {height: self.get_height(), width: self.get_width()};
                console.log('drag init:',self._startsize);
            });
            this.$('.js_vresizer').drag(function(event,dragevent){
                self.set_height(self._startsize.height + dragevent.deltaY);
            });
            this.$('.js_hresizer').drag(function(event,dragevent){
                self.set_height(self._startsize.height + dragevent.deltaY);
                self.set_width(self._startsize.width + dragevent.deltaX);
            });
        },
        get_collumns: function(){
            return this._collumns;
        },
        get_rows: function(){
            return this._rows;
        },
        add_row: function(row){
            this._rows.push(row);
            this.renderElement();
        },
        get_title: function(){
            return this._title;
        },
        get_width: function(){
            return this._width;
        },
        get_innerwidth: function(){
            return this._width - this._scrollbarwidth;
        },
        set_width: function(width){
            if(width >= 0){
                this._width = width;
                this.$('.js_innerwidth').css({'width':this.get_innerwidth()+'px'});
                this.$el.css({'width':this.get_width()+'px'});
            }
        },
        get_height: function(){
            return this._height;
        },
        set_height: function(height){
            if(height >= 0){
                this._height = height;
                this.$('.js_height').css({'height':this.get_height()+'px'});
            }
        },
    });

    module.PickingEditorWidget = instance.web.Widget.extend({
        template: 'PickingEditorWidget',
        get_header: function(){
            return 'Picking: INTERNAL/00112';
        },
        get_rows: function(){
            return [
                { cols: { product:'abc', qty:1, rem: 4, uom: 5, loc: 'def', stat: 'available' },   },
                { cols: { product:'dec', qty:2, rem: 3, uom: 5, loc: 'rcd', stat: 'available' },  classes: 'oe_invalid' },
                { cols: { product:'qcr', qty:4, rem: 4, uom: 5, loc: 'hre', stat: 'unavailable' }, },
            ];
        },
    });

    module.PackageEditorWidget = instance.web.Widget.extend({
        template: 'PackageEditorWidget',
        get_header: function(){
            return 'Package: 032 ';
        },
        get_rows: function(){
            return [
                { cols: { product:'abc', qty:1, uom: 5, },   },
                { cols: { product:'dec', qty:2, uom: 5, },  classes: 'oe_invalid' },
                { cols: { product:'qcr', qty:4, uom: 5, }, },
            ];
        },
    });

    module.PackageSelectorWidget = instance.web.Widget.extend({
        template: 'PackageSelectorWidget',
        get_header: function(){
            return 'Package Selector';
        },
        get_rows: function(){
            return [
                { cols: { pack:'abc' },   },
                { cols: { pack:'def' }, classes: 'oe_invalid'   },
                { cols: { pack:'ghi' },   },
            ];
        },
        increment: function(){
        },
        decrement: function(){
        },
    });

    module.PickingMainWidget = instance.web.Widget.extend({
        template: 'PickingMainWidget',
        init: function(){

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
