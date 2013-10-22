function openerp_wh_hide(openerp) {
   var module = openerp.stock;
   var _t = openerp.web._t;

   openerp.web.form.FieldMany2ManyCheckBoxes.include({	
	render_value: function(){
            this._super();
            var self = this;
	    setTimeout(function () {
		self.ShowHide();
            }, 0);
        },
	from_dom: function(){
            this._super();
            this.ShowHide();
        },
	ShowHide: function() {
	    var bShow = false;
	    this.$("input").each(function() {
		bShow = bShow || ($(this).attr("checked") ? true : false)
	    });
	    if (bShow) {
	        $(".resupply_ids").show();
            }
	    else {
   	        $(".resupply_ids").hide();
	    }		
	}
	
    });

    openerp.web.form.custom_widgets.add("m2m_hide_resupply","openerp.stock.manageResupply");
	
	//var a = false; $(".m2m_whids div").find(':checkbox').each( function(){ a = a | $(this)[0].checked; } ); alert(a);
}
