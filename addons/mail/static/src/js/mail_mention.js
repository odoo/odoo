odoo.define('mail.mention', function (require) {
"use strict";

var core = require('web.core');
var Model = require('web.Model');
var Widget = require('web.Widget');
var form_common = require('web.form_common');

var _t = core._t;
var QWeb = core.qweb;

/**
 * ------------------------------------------------------------
 * Mention widget
 * ------------------------------------------------------------
 *
 * This widget handles @ mention functionality.
 * Open dropdown when user mention partner with @
 * Dropdown open with highlighted string
 * Start search if word have minimum length is 3
 * Wait for at least 400 milliseconds without typing any new letter
 * Maximum number of partner in dropdown list is 8
 */
var Mention = Widget.extend({
    init: function(parent, $el, options) {
        this._super.apply(this, arguments);
        this.$textarea = $el;
        this.$dropdown = $("<div class='o_mail_mention_main'><ul></ul></div>");
        this.model_res_partner = new Model("res.partner");
        this.selected_partners = {};
        this.search_keys = {};
        this.partners = {};
        this.keyup_list = [40, 38, 13, 35, 33, 34, 27];
        this.partner_limit = options['partner_limit'] || 8;
        this.typing_speed = options['typing_speed'] || 400;
        this.min_charactor = options['min_charactor'] || 4;
        this.search_string = '';
        this.recent_string = '';
    },

    start: function() {
        var return_value = this._super.apply(this, arguments);
        this.bind_events();
        return return_value;
    },
    bind_events: function() {
        var self = this;
        this.$dropdown.insertAfter(this.$textarea);
        
        //textear event binding
        this.$textarea.on('keyup', this.proxy('textarea_keyup'))
        .on('click', function(e){ self.clear_dropdown(); })
        .on('keydown', function(e){
            var $active = self.$dropdown.find("li.active");
            if(self.recent_string){
                if (e.keyCode == 40) {
                    $active.next().trigger("mouseover");
                    return false;
                } else if (e.keyCode == 38) {
                    $active.prev().trigger("mouseover");
                    return false;
                } else if(e.keyCode == 13){
                    self.find_n_replace(parseInt($active.find("span").attr("id")));
                    return false;
                }
            }
        });
        
        //dropdown event binding
        this.$dropdown.on('mouseover', 'li', function(e) {
            $(e.currentTarget).addClass('active').siblings().removeClass();
        }).on('click', 'li', function(e){
            self.find_n_replace(parseInt($(e.currentTarget).find("span").attr("id")));
        });
        this.clear_dropdown();
    },
    show_dropdown: function(){
        var self = this;
        var highlight = function(description){
            if(description)
            return description.replace(new RegExp(self.search_string, "gi"), function(str) {return _.str.sprintf("<b><u>%s</u></b>",str);});};

        var res = _.map(self.search_keys[self.search_string], function(id) {
                return {
                    "id": id, 
                    "name": highlight(self.partners[id]["name"]), 
                    "email": highlight(self.partners[id]["email"])
                    };
        });
        this.clear_dropdown();
        this.$dropdown.find("ul").append(QWeb.render('Mention', {"result": res}));
        this.$dropdown.find("li:first").addClass("active");
        this.$dropdown.find("ul").show();
    },

    clear_dropdown: function() {
        this.$dropdown.find("ul").hide();
        this.$dropdown.find("ul").empty();
    },
    
    search_n_store: function() {
        var self = this;
        if(!this.search_keys[this.search_string] && this.recent_string) {
            this.model_res_partner.call("search_read", {
                domain: ['|', ['name', 'ilike', self.search_string], ['email', 'ilike', self.search_string]],
                fields: ['name', 'email'],
                limit: this.partner_limit
            }).done(function(res) {
                if(!res.length) return;
                _.each(res, function(r) {self.partners[r.id] = r;});
                self.search_keys[self.search_string] = _.pluck(res, "id");
                self.show_dropdown();
            });
            return;
        }
        self.show_dropdown();
    },
    find_n_test: function(){
        var self = this;
        var test_string = function(search_str){
             var pattern = /(^@|(^\s@))/g;
             var regex_start = new RegExp(pattern);
             if (regex_start.test(search_str) && search_str.length >= self.min_charactor ){
                 search_str = _.str.ltrim(search_str.replace(pattern, ''));
                 return search_str.indexOf(' ') < 0 &&  _.isNull(/\r|\n/.exec(search_str))? search_str:'';
             }
            return '';
        };
        var desctiption = this.$textarea.val(),
        left_string = desctiption.substring(0, this.get_cursor_position(this.$textarea)),
        search_str = desctiption.substring(left_string.lastIndexOf("@") - 1, this.get_cursor_position(this.$textarea));
        return test_string(search_str);
    },
    textarea_keyup: function(e) {
        var self = this;
        if(_.contains(this.keyup_list, e.which)) { return;}
        
        this.recent_string = this.find_n_test();
        if(this.recent_string){
            this.search_string = this.recent_string;
            clearTimeout(this.timer);
            this.timer = setTimeout(function() {
                self.search_n_store();
            }, this.typing_speed);
        }else if(this.$dropdown.find("li")){
            this.clear_dropdown();
        }
    },

    show_form_popup: function(email){
        var deferred = $.Deferred();
        if(email){
            deferred.resolve();
            return deferred;
        }
        var partner_form_popup = new form_common.FormOpenPopup(this);
            partner_form_popup.show_element(
                'res.partner',
                id,
                {
                    'force_email': true,
                    'ref': "compound_context",
                    'default_name': name
                },
                {
                    title: _t("Please complete partner's informations"),
                    write_function: function(id, data, options) {
                        return this._super(id, data, options).done(function() {
                            if(data.name)
                                self.partners[id]['name'] = data.name;
                            self.partners[id]['email'] = data.email;
                            deferred.resolve();
                        });
                    },
                }
            );
            partner_form_popup.on('closed', self, function() {
                self.$textarea.focus();
            });
        return deferred;
    },
    find_n_replace: function(id) {
        var self = this;
        var partner = this.partners[id],
            name = partner["name"], 
            email = partner["email"];
        
        this.show_form_popup(email).done(function() {
            self.clear_dropdown();
            self.selected_partners[id] = name;
            var index = self.get_cursor_position(self.$textarea), value = self.$textarea.val();
            self.$textarea.val(_.str.sprintf("%s%s%s", 
                    value.substring(0, index - self.search_string.length), 
                    name, 
                    value.substring(index, value.length)));
            self.set_cursor_position(self.$textarea, index - self.search_string.length + name.length);
        });
    },
    get_cursor_position: function(ctrl) {
        var el = $(ctrl).get(0);
        if(!el) {return 0};
        if('selectionStart' in el) {
            return el.selectionStart;
        } else if('selection' in document) {
            var cr = document.selection.createRange();
            return cr.moveStart('character', -el.focus().value.length).text.length - cr.text.length;
        }
        return 0;
    },

    set_cursor_position: function(ctrl, pos) {
        ctrl.each(function(index, elem) {
            if (elem.setSelectionRange){
              elem.setSelectionRange(pos, pos);
            }
            else if (elem.createTextRange){
              elem.createTextRange().collapse(true).moveEnd('character', pos).moveStart('character', pos).select();
            }
          });
        return ctrl;
    }
});

return Mention;

});