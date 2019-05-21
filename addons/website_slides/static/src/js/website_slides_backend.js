odoo.define('website_slides.backend', function(require){
    "use strict";

    
    var core = require('web.core');
    var KanbanController = require('web.KanbanController');

    var qweb = core.qweb;

    KanbanController.include({
        renderButtons: function($node){
            if(this.hasButtons && this.is_action_enabled('create')){
                if(this.modelName == 'slide.channel'){
                    this.$buttons = $(qweb.render('KanbanView.buttons.course',{
                        widget: this,
                    }));
                }else{
                    this.$buttons = $(qweb.render('KanbanView.buttons',{
                        btnClass: 'btn-primary',
                        widget: this,
                    }));
                }
                
                this.$buttons.on('click', 'button.o-kanban-button-new', this._onButtonNew.bind(this));
                this.$buttons.on('keydown',this._onButtonsKeyDown.bind(this));
                this._updateButtons();
                this.$buttons.appendTo($node);
            }
        },
    });

    core.action_registry.add('website_slides.backend', KanbanController);
    return KanbanController;
});