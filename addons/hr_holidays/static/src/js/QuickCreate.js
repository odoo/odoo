openerp.hr_holidays = function(instance) {
    var _t = instance.web._t;
    var QWeb = instance.web.qweb;
    instance.hr_holidays = {}
 /**
     * Quick creation view.
     *
     * Triggers a single event "added" with a single parameter "name", which is the
     * name entered by the user
     *
     * @class
     * @type {*}
     */
    instance.hr_holidays.QuickCreate = instance.web_calendar.QuickCreate.extend({ 
        template: 'hr_holidays.QuickCreate',

        /**
         * close_btn: If true, the widget will display a "Close" button able to trigger
         * a "close" event.
         */
        init: function(parent, dataset, buttons, options, data_template) {
            this._super(parent);            

            this.dataset = dataset;
            this._buttons = buttons || false;
            this.options = options;

            //this.options.disable_quick_create = true;
            
            // Can hold data pre-set from where you clicked on agenda
            this.data_template = data_template || {};
        },
       
       
        start: function() {
            var self=this;
            this._super();
            
            new instance.web.Model("hr.holidays.status").query(["name"]).filter([["active", "=",true]]).all().then(function(result) {
                var holidays_status = {};
                
                _.each(result, function(item) {
                    var filter_item = {
                        value: item.id,
                        label: item.name,
                    };
                    holidays_status[item.id] = filter_item;
                });
                
                var optionType = QWeb.render('hr_holidays.QuickCreate.select', { elements: holidays_status });
                console.log(optionType);
                $(".qc_type").html(optionType);
           });
            
        },
        
        focus: function() {
            this.$el.find('input').focus();
        },

        /**
         * Gathers data from the quick create dialog a launch quick_create(data) method
         */
        quick_add: function() {
            var name = this.$el.find(".qc_name").val();
            var type = this.$el.find(".qc_type").val();
            
            if (/^\s*$/.test(name)) { return; }
            this.quick_create({'name': name,'holiday_status_id':parseInt(type)});
        },

        
        slow_add: function() {
            var name = this.$el.find(".qc_name").val();
            var type = this.$el.find(".qc_type").val();
            this.slow_create({'name': name,'holiday_status_id':parseInt(type)});
        },

    });
 
};
