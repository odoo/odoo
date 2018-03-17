odoo.define('hotel_pos_restaurant.folio', function (require) {
	"use strict";

//	screens.ActionpadWidget.include({
//	    renderElement: function() {
//	        var self = this;
//	        this._super();
//	        
//	        this.$('.button').click(function(){
//	        	
//	        	var self = this;
//                this._super(parent, options);
//
//                this.pos.bind('change:selectedFolio', function() {
//                    self.renderElement();
//                });
//            },
//            renderElement: function() {
//                var self = this;
//                this._super();
//                self.gui.show_screen('folio');
//                this.$('.set-folio').click(function(){
//                    self.gui.show_screen('foliolist');
//                });
//            }
//	        	
//	           var PosBaseWidget = require('point_of_sale.BaseWidget');
//	           var gui = require('point_of_sale.gui');
//	           var models = require('point_of_sale.models');
//	            
//	            /*--------------------------------------*\
//	            |          THE DOM CACHE               |
//	           \*======================================*/
//
//	           // The Dom Cache is used by various screens to improve
//	           // their performances when displaying many time the 
//	           // same piece of DOM.
//	           // It is a simple map from string 'keys' to DOM Nodes.
//	           // The cache empties itself based on usage frequency 
//	           // stats, so you may not always get back what
//	           // you put in.
//
//	           this.folio_cache = new DomCache();
//	           var DomCache = core.Class.extend({
//	               init: function(options){
//	                   options = options || {};
//	                   this.max_size = options.max_size || 2000;
//	                   
//	                   this.cache = {};
//	                   this.access_time = {};
//	                   this.size = 0;
//	               },
//	               cache_node: function(key,node){
//	                   var cached = this.cache[key];
//	                   this.cache[key] = node;
//	                   this.access_time[key] = new Date().getTime();
//	                   if(!cached){
//	                       this.size++;
//	                       while(this.size >= this.max_size){
//	                           var oldest_key = null;
//	                           var oldest_time = new Date().getTime();
//	                           for(key in this.cache){
//	                               var time = this.access_time[key];
//	                               if(time <= oldest_time){
//	                                   oldest_time = time;
//	                                   oldest_key  = key;
//	                               }
//	                           }
//	                           if(oldest_key){
//	                               delete this.cache[oldest_key];
//	                               delete this.access_time[oldest_key];
//	                           }
//	                           this.size--;
//	                       }
//	                   }
//	                   return node;
//	               },
//	               clear_node: function(key) {
//	                   var cached = this.cache[key];
//	                   if (cached) {
//	                       delete this.cache[key];
//	                       delete this.access_time[key];
//	                       this.size --;
//	                   }
//	               },
//	               get_node: function(key){
//	                   var cached = this.cache[key];
//	                   if(cached){
//	                       this.access_time[key] = new Date().getTime();
//	                   }
//	                   return cached;
//	               },
//	           });
//	           
//	        // these dynamic attributes can be watched for change by other models or widgets
//	           this.set({
//	               'synch':            { state:'connected', pending:0 }, 
//	               'orders':           new OrderCollection(),
//	               'selectedOrder':    null,
//	               'selectedFolio':   null,
//	           });
//
//	           this.get('orders').bind('remove', function(order,_unused_,options){ 
//	               self.on_removed_order(order,options.index,options.reason); 
//	           });
//
//	           // Forward the 'folio' attribute on the selected order to 'selectedFolio'
//	           function update_folio() {
//	               var order = self.get_order();
//	               this.set('selectedFolio', order ? order.get_folio() : null );
//	           }
//	           this.get('orders').bind('add remove change', update_folio, this);
//	           this.bind('change:selectedOrder', update_folio, this);
//	            
//	            /*--------------------------------------*\
//	            |         THE FOLIO LIST              |
//	           \*======================================*/
//
//	           var FolioListScreenWidget = ScreenWidget.extend({
//	               template: 'FolioListScreenWidget',
//
//	               init: function(parent, options){
//	                   this._super(parent, options);
//	                   this.partner_cache = new DomCache();
//	               },
//
//	               auto_back: true,
//
//	               show: function(){
//	                   var self = this;
//	                   this._super();
//
//	                   this.renderElement();
//	                   this.details_visible = false;
//	                   this.old_folio = this.pos.get_order().get_folio();
//
//	                   this.$('.back').click(function(){
//	                       self.gui.back();
//	                   });
//
//	                   this.$('.next').click(function(){   
//	                       self.save_changes();
//	                       self.gui.back();    
//	                   });
//
//	                   if( this.old_folio ){
//	                       this.display_folio_details('show',this.old_folio,0);
//	                   }
//
//	                   this.$('.folio-list-contents').delegate('.folio-line','click',function(event){
//	                       self.line_select(event,$(this),parseInt($(this).data('id')));
//	                   });
//
//	               },
//	               folio_changed: function() {
//	                   var folio = this.pos.get_folio();
//	                   this.$('.js_folio_name').text( folio ? folio.name : _t('Folio') ); 
//	               },
//	               click_set_folio: function(){
//	                   this.gui.show_screen('foliolist');
//	               },
//	               click_back: function(){
//	                   this.gui.show_screen('products');
//	               },
//	               hide: function () {
//	                   this._super();
//	                   this.new_folio = null;
//	               },
//	               barcode_folio_action: function(code){
//	                   if (this.editing_folio) {
//	                       this.$('.detail.barcode').val(code.code);
//	                   } else if (this.pos.db.get_partner_by_barcode(code.code)) {
//	                       var folio = this.pos.db.get_partner_by_barcode(code.code);
//	                       this.new_folio = folio;
//	                       this.display_folio_details('show', folio);
//	                   }
//	               },
//	               perform_search: function(query, associate_result){
//	                   var folio;
//	                   if(query){
//	                       folio = this.pos.db.search_partner(query);
//	                       this.display_folio_details('hide');
//	                       if ( associate_result && folio.length === 1){
//	                           this.new_folio = folio[0];
//	                           this.save_changes();
//	                           this.gui.back();
//	                       }
//	                       this.render_list(folio);
//	                   }else{
//	                       folio = this.pos.db.get_partners_sorted();
//	                       this.render_list(folio);
//	                   }
//	               },
//	               clear_search: function(){
//	                   var folio = this.pos.db.get_partners_sorted(1000);
//	                   this.render_list(folio);
//	               },
//	               render_list: function(folio){
//	                   var contents = this.$el[0].querySelector('.folio-list-contents');
//	                   contents.innerHTML = "";
//	                   for(var i = 0, len = Math.min(partners.length,1000); i < len; i++){
//	                       var folio    = folio[i];
//	                       var folioline = this.folio_cache.get_node(folio.id);
//	                       if(!folioline){
//	                           var folioline_html = QWeb.render('folioline',{widget: this, folio:folio[i]});
//	                           var folioline = document.createElement('tbody');
//	                           folioline.innerHTML = folioline_html;
//	                           folioline = folioline.childNodes[1];
//	                           this.folio_cache.cache_node(folio.id,folioline);
//	                       }
//	                       if( partner === this.old_folio ){
//	                           folioline.classList.add('highlight');
//	                       }else{
//	                           folioline.classList.remove('highlight');
//	                       }
//	                       contents.appendChild(folioline);
//	                   }
//	               },
//	               save_changes: function(){
//	                   var self = this;
//	                   var order = this.pos.get_order();
//	                   if( this.has_folio_changed() ){
//	                       if ( this.new_folio ) {
//	                           order.fiscal_position = _.find(this.pos.fiscal_positions, function (fp) {
//	                               return fp.id === self.new_folio.property_account_position_id[0];
//	                           });
//	                       } else {
//	                           order.fiscal_position = undefined;
//	                       }
//
//	                       order.set_folio(this.new_folio);
//	                   }
//	               },
//	               has_folio_changed: function(){
//	                   if( this.old_folio && this.new_folio ){
//	                       return this.old_folio.id !== this.new_folio.id;
//	                   }else{
//	                       return !!this.old_folio !== !!this.new_folio;
//	                   }
//	               },
//	               toggle_save_button: function(){
//	                   var $button = this.$('.button.next');
//	                   if (this.editing_folio) {
//	                       $button.addClass('oe_hidden');
//	                       return;
//	                   } else if( this.new_folio ){
//	                       if( !this.old_folio){
//	                           $button.text(_t('Set Folio'));
//	                       }else{
//	                           $button.text(_t('Change Folio'));
//	                       }
//	                   }else{
//	                       $button.text(_t('Deselect Folio'));
//	                   }
//	                   $button.toggleClass('oe_hidden',!this.has_folio_changed());
//	               },
//	               line_select: function(event,$line,id){
//	                   var partner = this.pos.db.get_partner_by_id(id);
//	                   this.$('.folio-list .lowlight').removeClass('lowlight');
//	                   if ( $line.hasClass('highlight') ){
//	                       $line.removeClass('highlight');
//	                       $line.addClass('lowlight');
//	                       this.display_folio_details('hide',folio);
//	                       this.new_folio = null;
//	                       this.toggle_save_button();
//	                   }else{
//	                       this.$('.folio-list .highlight').removeClass('highlight');
//	                       $line.addClass('highlight');
//	                       var y = event.pageY - $line.parent().offset().top;
//	                       this.display_folio_details('show',folio,y);
//	                       this.new_folio = partner;
//	                       this.toggle_save_button();
//	                   }
//	               },
//	               this.$('.folio-list-contents').delegate('.folio-line','click',function(event){
//	                   self.line_select(event,$(this),parseInt($(this).data('id')));
//	               });
//
//	               display_folio_details: function(visibility,partner,clickpos){
//	                   var self = this;
//	                   var contents = this.$('.folio-details-contents');
//	                   var parent   = this.$('.folio-list').parent();
//	                   var scroll   = parent.scrollTop();
//	                   var height   = contents.height();
//
//	                   contents.off('click',y'.button.save'); 
//	                   if(visibility === 'show'){
//	                       contents.empty();
//	                       contents.append($(QWeb.render('hotel_pos_restaurant.FolioListScreenWidget',{widget:this,folio:folio})));
//
//	                       var new_height   = contents.height();
//
//	                       if(!this.details_visible){
//	                           parent.height('-=' + new_height);
//
//	                           if(clickpos < scroll + new_height + 20 ){
//	                               parent.scrollTop( clickpos - 20 );
//	                           }else{
//	                               parent.scrollTop(parent.scrollTop() + new_height);
//	                           }
//	                       }else{
//	                           parent.scrollTop(parent.scrollTop() - height + new_height);
//	                       }
//
//	                       this.details_visible = true;
//	                       this.toggle_save_button();
//	                   }
//	               },
//	               saved_folio_details: function(folio_id){
//	                   var self = this;
//	                   this.reload_folios().then(function(){
//	                       var folio = self.pos.db.get_folio_by_id(folio_id);
//	                       if (folio) {
//	                           self.new_folio = folio;
//	                           self.toggle_save_button();
//	                           self.display_folio_details('show',folio);
//	                       } else {
//	                           self.display_folio_details('hide');
//	                       }
//	                   });
//	               },
//	               reload_folios: function(){
//	                   var self = this;
//	                   return this.pos.folios().then(function(){
//	                       self.render_list(self.pos.db.get_partners_sorted(1000));
//	                       
//	                       // update the currently assigned folio if it has been changed in db.
//	                       var curr_folio = self.pos.get_order().get_folio();
//	                       if (curr_folio) {
//	                           self.pos.get_order().set_folio(self.pos.db.get_folio_by_id(curr_folio.id));
//	                       }
//	                   });
//	               },
//
//	               close: function(){
//	                   this._super();
//	               },
//	           });
//	           gui.define_screen({name:'foliolist', widget: FolioListScreenWidget});
//	   self.gui.show_screen('FolioListScreenWidget');
});
