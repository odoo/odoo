odoo.define('hide_or_show_password.password_eye', function(require) {
    'use strict';
    
    var basic_fields = require('web.basic_fields');
    var InputField = basic_fields.InputField;
    const { patch } = require('web.utils');
    var core = require('web.core');
    var qweb = core.qweb;

    InputField.include({
        _renderEdit: function () {
            this._prepareInput(this.$el);
            if (this.nodeOptions.show_or_hide) {
                console.log(this)
                if ($(this.$el).length && this.nodeOptions.isPassword){
                    var element = this.$el;
                    var self = this
                    $(document).ready(function(e){
                        var style = $(self).attr('style')
                        $(element).attr('style', 'width: calc(100% - 28px);' + style)
                        var idIcon = 'ic_' + $(element).attr('id')
                        var icon = $('<i/>').addClass('fa fa-eye show__password').attr('id', idIcon)
                        $(element).after(icon)
                        
                        $(icon).click(function(e){
                            if($(element).attr('type') == 'password'){
                                $(icon).removeClass('fa-eye').addClass('fa-eye-slash');
                                $(element).attr('type', 'text')
                            }else{
                                $(icon).removeClass('fa-eye-slash').addClass('fa-eye');
                                $(element).attr('type', 'password')
                            }
                        })
                    })
                }
            }
        },
        _renderReadonly: function () {
            this.$el.text(this._formatValue(this.value));
            if (this.nodeOptions.show_or_hide) {
                if ($(this.$el).length && this.nodeOptions.isPassword){
                    var element = this.$el;
                    var self = this
                    $(document).ready(function(e){
                        var style = $(self).attr('style')
                        $(element).attr('style', 'width: calc(100% - 28px);' + style)
                        var idIcon = 'ic_' + $(element).attr('id')
                        var classIcon = 'fa fa-eye show__password'
                        if ($(element).hasClass('o_invisible_modifier')) {
                            classIcon += ' o_invisible_modifier'
                        }
                        var icon = $('<i/>').addClass(classIcon).attr('id', idIcon)
                        $(element).after(icon)
                        
                        $(icon).click(function(e){
                            if($(icon).hasClass('fa-eye')){
                                $(icon).removeClass('fa-eye').addClass('fa-eye-slash');
                                $(element).text(self.value);
                            }else{
                                $(icon).removeClass('fa-eye-slash').addClass('fa-eye');
                                $(element).text(self._formatValue(self.value));
                            }
                        })
                    })
                }
            }
        },
    });

});