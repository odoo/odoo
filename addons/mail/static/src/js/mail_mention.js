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
        this.partner_limit = options['partner_limit'] || 8;
        this.typing_speed = options['typing_speed'] || 400;
        this.min_charactor = options['min_charactor'] || 4;
        this.search_string = '';
        this.recent_string = '';
        this.set('partners', []);
        var keycode = $.ui.keyCode;
        this.escape_keys = [keycode.DOWN,
                            keycode.UP,
                            keycode.ENTER,
                            keycode.END,
                            keycode.PAGE_UP,
                            keycode.PAGE_DOWN,
                            keycode.ESCAPE];
    },

    start: function() {
        var return_value = this._super.apply(this, arguments);
        this.bind_events();
        return return_value;
    },
    bind_events: function() {
        var self = this;
        this.$dropdown.insertAfter(this.$textarea);
        this.$textarea.on('keyup', this.proxy('textarea_keyup'))
        .on('click', function(){ self.clear_dropdown(); })
        .on('keydown', function(e){
            var $active = self.$dropdown.find("li.active");
            if(self.recent_string){
                switch(e.keyCode) {
                    case $.ui.keyCode.DOWN:
                        $active.next().addClass('active').siblings().removeClass();
                        break;
                    case $.ui.keyCode.UP:
                        $active.prev().addClass('active').siblings().removeClass();
                        break;
                    case $.ui.keyCode.ENTER:
                        self.replace_partner_text($active.find("span").data("id"));
                        e.preventDefault();
                        break;
                }
            }
        });

        this.$dropdown.on('mouseover', 'li', function(e) {
            $(e.currentTarget).addClass('active').siblings().removeClass();
        }).on('click', 'li', function(e){
            self.replace_partner_text($(e.currentTarget).find("span").data("id"));
        });
        this.on('change:partners', this, this.show_dropdown);
        this.clear_dropdown();
    },
    show_dropdown: function(){
        var self = this;
        var highlight = function(description){
                if(description){
                    return description.replace(new RegExp(self.search_string, "gi"), function(str){
                        return _.str.sprintf("<b><u>%s</u></b>", str);
                    });
                }
            },
        escape_ids = _.keys(this.selected_partners),
        partners = _.filter(this.get('partners'), function(partner){
                            return !_.contains(escape_ids, partner.id.toString());
                        });
        var res = _.map(partners, function(partner) {
            return {
                "id": partner["id"],
                "name": highlight(partner["name"]),
                "email": highlight(partner["email"])
            };
        });
        this.clear_dropdown();
        this.$dropdown.find("ul").append(QWeb.render('Mention', {"partners": res})).show();
        this.$dropdown.find("li:first").addClass("active");
    },
    clear_dropdown: function() {
        this.$dropdown.find("ul").empty().hide();
    },
    set_partners: function() {
        var self = this;
        if(this.recent_string) {
            this.model_res_partner.call("search_read", {
                domain: ['|', ['name', 'ilike', self.search_string], ['email', 'ilike', self.search_string]],
                fields: ['name', 'email'],
                limit: this.partner_limit
            }).done(function(res) {
                if(!res.length) return;
                self.set('partners', res);
            });
        }
    },
    detect_at_keyword: function(){
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
        if(_.contains(this.escape_keys, e.which)) {
            return ;
        }
        this.recent_string = this.detect_at_keyword();
        if(this.recent_string){
            this.search_string = this.recent_string;
            clearTimeout(this.timer);
            this.timer = setTimeout(function() {
                self.set_partners();
            }, this.typing_speed);
        }else if(this.$dropdown.find("li")){
            this.clear_dropdown();
        }
    },
    preprocess_mention_post: function(post_body, mention_callback){
        var self = this;
        _.each(this.selected_partners, function(value, key){
            var word = _.str.sprintf("@%s", value);
            if(post_body.indexOf(word) != -1) {
                post_body = post_body.replace(word, _.str.sprintf("@<span data-oe-model='res.partner' data-oe-id='%s'>%s</span> ", key, value));
                return;
            }
            delete self.selected_partners[key];
        });
        mention_callback(post_body, self.selected_partners);
    },
    validate_partner_email: function(partner){
        var self = this,
            deferred = $.Deferred();
        if(partner.email){
            deferred.resolve(partner);
            return deferred;
        }
        var form_pop = new form_common.FormViewDialog(self, {
                res_model: 'res.partner',
                res_id: partner.id,
                context: {
                    'force_email': true,
                    'ref': "compound_context",
                    'default_name': partner.name,
                },
                title: _t("Please provide partner email address"),
                write_function: function(id, data, options) {
                    return this._super(id, data, options).done(function() {
                        if(data.email){
                            partner.email = data.email;
                        }
                        deferred.resolve(partner);
                    });
                },
            }).open();
        form_pop.on('closed', self, function() {
            self.$textarea.focus();
        });
        return deferred;
    },
    replace_partner_text: function(partner_id) {
        var self = this;
        var partner = _.find(this.get('partners'), function(partner){return partner.id == partner_id;});
        if (!partner){
            return false;
        }
        this.validate_partner_email(partner).done(function(partner) {
            self.clear_dropdown();
            self.selected_partners[partner_id] = partner.name;
            var index = self.get_cursor_position(self.$textarea),
                value = self.$textarea.val();
            self.$textarea.val(_.str.sprintf("%s%s%s ",
                    value.substring(0, index - self.search_string.length),
                    partner.name,
                    value.substring(index, value.length)));
            self.set_cursor_position(self.$textarea, index - self.search_string.length + partner.name.length + 1);
        });
    },
    get_cursor_position: function($el) {
        var el = $el.get(0);
        if(!el){
            return 0;
        }
        if('selectionStart' in el) {
            return el.selectionStart;
        } else if('selection' in document) {
            var cr = document.selection.createRange();
            return cr.moveStart('character', -el.focus().value.length).text.length - cr.text.length;
        }
        return 0;
    },

    set_cursor_position: function($el, pos) {
        $el.each(function(index, elem) {
            if (elem.setSelectionRange){
                elem.setSelectionRange(pos, pos);
            }
            else if (elem.createTextRange){
                elem.createTextRange().collapse(true).moveEnd('character', pos).moveStart('character', pos).select();
            }
        });
    }
});

return Mention;

});