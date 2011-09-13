openerp.base.view_editor = function(openerp) {
openerp.base.ViewEditor =  openerp.base.Widget.extend({
    init: function(parent, element_id, dataset, view, options) {
        this._super(parent);
        this.element_id = element_id
        this.parent = parent
        this.dataset = dataset;
        this.model = dataset.model;
        this.xml_id = 0;
    },
    start: function() {
        this.View_editor();
    },
    View_editor : function(){
        var self = this;
        var action = {
            name:'ViewEditor',
            context:this.session.user_context,
            domain: [["model", "=", this.dataset.model]],
            res_model: 'ir.ui.view',
            views : [[false, 'list']],
            type: 'ir.actions.act_window',
            target: "current",
            limit : 80,
            auto_search : true,
            flags: {
                sidebar: false,
                views_switcher: false,
                action_buttons:false,
                search_view:false,
                pager:false,
                radio:true
            },
        };
        var action_manager = new openerp.base.ActionManager(this);
        this.dialog = new openerp.base.Dialog(this,{
            modal: true,
            title: 'ViewEditor',
            width: 750,
            height: 500,
            buttons: {
                "Create": function(){
                    
                },
                "Edit": function(){
                    self.xml_id=0;
                    self.edit_view();
                },
                "Close": function(){
                 $(this).dialog('destroy');
                }
            },

        });
       this.dialog.start(); 
       this.dialog.open();
       action_manager.appendTo(this.dialog);
       action_manager.do_action(action);


    },
    check_attr:function(xml,tag){
        var obj = new Object();
        obj.child_id = [];
        obj.id = this.xml_id++;
        var att_list = [];
        var name1 = "<" + tag;
        $(xml).each(function() {
            att_list = this.attributes;
            att_list = _.select(att_list, function(attrs){
                if(attrs.nodeName == "string" || attrs.nodeName == "name" || attrs.nodeName == "index"){
                    name1 += ' ' +attrs.nodeName+'='+'"'+attrs.nodeValue+'"';} 
                });
                name1+= ">";
         });  
        obj.name = name1;
        return obj;
    },
    recursiveFunction : function(main_object,parent_id,child_id){
        var self = this;
        var check = false;
        var main_object = _.detect(main_object , function(node){
            if(node.id == parent_id){   
                node.child_id = child_id;
                check = true;
             }
            return main_object;
        });
        if(check){
            return main_object;
        }else{ 
            //todo recursion for saving object into objects        
        }
    },
    children_function : function(xml,root,main_object,parent_id){
        var self = this;
        var child_obj_list = [];
        var main_object = main_object;
        var children_list = $(xml).filter(root).children();
        _.each(children_list, function(child_node){
            var string = self.check_attr(child_node,child_node.tagName.toLowerCase());
            child_obj_list.push(string);
        });
        if(children_list.length != 0){
            main_object = self.recursiveFunction(main_object,parent_id,child_obj_list); 
        }
        for(var i=0;i<children_list.length;i++){
            self.children_function(children_list[i],children_list[i].tagName.toLowerCase(),main_object,child_obj_list[i].id);
        }
        return child_obj_list;
    },
    edit_view : function(){
            var self = this;
            var view_id =(($("input[name='radiogroup']:checked").parent()).parent()).attr('data-id');
            var ve_dataset = new openerp.base.DataSet(this,'ir.ui.view');
            ve_dataset.read_ids([parseInt(view_id)],['arch'],function (arch) {
            var arch = arch[0].arch;
            var root = $(arch).filter(":first")[0];
            var tag = root.tagName.toLowerCase();
            var root_object = self.check_attr(root,tag);
            var all_list = self.children_function(arch,tag,[root_object],root_object.id);
            
            //todo render the final object of tree view so xml with it child node display...            
            });
            this.dialog = new openerp.base.Dialog(this,{
            modal: true,
            title: 'Edit Xml',
            width: 750,
            height: 500,
            buttons: {
                "Inherited View": function(){
                    
                },
                "Preview": function(){
                    
                },
                "Close": function(){
                    $(this).dialog('destroy');
                }
            },

        });
         this.dialog.start().open();
    }
        
});
};
