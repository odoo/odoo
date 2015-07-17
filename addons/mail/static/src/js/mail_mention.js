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
        this.options = _.defaults(options || {}, {'partner_limit': 8, 'typing_speed': 400, 'min_charactor': 3});
        this.$textarea = $el;
        this.$dropdown = $("<div class='o_mail_mention_main'><ul></ul></div>");
        this.model_res_partner = new Model("res.partner");
        this.selected_partners = [];
        this.search_string = '';
        this.recent_string = '';
        this.set('partners', []);
        var keycode = $.ui.keyCode;
        this.escape_keys = [keycode.DOWN,
                            keycode.UP,
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
        // TODO: Add textarea inside div from standard mail template
        this.$textarea.css({'width':'100%'}).wrap( "<div class='o_mail_mention_container'></div>" );
        this.$dropdown.insertAfter(this.$textarea);
        this.$textarea.on('keyup', this.proxy('textarea_keyup'))
        .on('click', function(){ self.clear_dropdown(); })
        .on('keydown', function(e){
            var $active = self.$dropdown.find("li.active");
            if(self.recent_string){
                switch(e.keyCode) {
                    case $.ui.keyCode.DOWN:
                        $active.next().addClass('active').siblings().removeClass();
                        e.preventDefault();
                        break;
                    case $.ui.keyCode.UP:
                        $active.prev().addClass('active').siblings().removeClass();
                        e.preventDefault();
                        break;
                    case $.ui.keyCode.ENTER:
                        var active_id = $active.find("span").data("id");
                        if(active_id){
                            self.replace_partner_text(active_id);
                            e.preventDefault();
                        }
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
    get_caret_position: function($el){
        // ref: https://github.com/ilkkah/textarea-caret-position
        var position = this.get_cursor_position($el),
            faux_div = $("<div>").appendTo('body').get(0),
            element = $el.get(0),
            style = faux_div.style,
            computed = window.getComputedStyle? getComputedStyle(element) : element.currentStyle;

        style.whiteSpace = 'pre-wrap';
        style.position = 'absolute';
        style.visibility = 'hidden';
        style.top = element.offsetTop + parseInt(computed.borderTopWidth) + 'px';

        var properties = ['direction','boxSizing','width','height','overflowX','overflowY','borderTopWidth',
        'borderRightWidth','borderBottomWidth','borderLeftWidth','paddingTop','paddingRight','paddingBottom','paddingLeft','fontStyle','fontVariant',
        'fontWeight','fontStretch','fontSize','lineHeight','fontFamily','textAlign','textTransform','textIndent','textDecoration', 'letterSpacing',
        'wordSpacing'];

        properties.forEach(function (prop) {
            style[prop] = computed[prop];
        });

        faux_div.textContent = element.value.substring(0, position);
        var span = document.createElement('span');
        span.textContent = element.value.substring(position) || '.';
        faux_div.appendChild(span);

        var offset = {
            top: span.offsetTop + parseInt(computed.borderTopWidth, 10),
            left: span.offsetLeft + parseInt(computed.borderLeftWidth, 10)
        };
        $(faux_div).remove();
        return offset;
    },
    show_dropdown: function(){
        var self = this;
        var highlight = function(description){
                if(description){
                    return description.replace(new RegExp(self.search_string, "gi"), function(str){
                        return _.str.sprintf("<b><u>%s</u></b>", str);
                    });
                }
            };
        var escape_ids = _.pluck(this.selected_partners, 'id');
        var res = _.filter(this.get('partners'), function(partner) {
            if (!_.contains(escape_ids, partner.id)){
                return {
                    "id": partner["id"],
                    "name": highlight(partner["name"]),
                    "email": highlight(partner["email"])
                };
            }
        });
        this.clear_dropdown();
        var offset = this.get_caret_position(this.$textarea);
        this.$dropdown.css({top: offset.top}).find("ul").append(QWeb.render('Mention', {"partners": res})).show();
        this.$dropdown.find("li:first").addClass("active");
    },
    clear_dropdown: function() {
        this.$dropdown.find("ul").empty().hide();
    },
    set_partners: function() {
        var self = this;
        if(this.recent_string) {
            // TODO: abort request when recent string not valid
            this.model_res_partner.call("search_read", {
                domain: ['|', ['name', 'ilike', self.search_string], ['email', 'ilike', self.search_string]],
                fields: ['name', 'email'],
                limit: this.options.partner_limit
            }).done(function(res) {
                if(!res.length) return;
                self.set('partners', res);
            });
        }
    },
    detect_at_keyword: function(){
        var self = this;
        var validate_keyword = function(search_str){
            var pattern = /(^@|(^\s@))/g;
            var regex_start = new RegExp(pattern);
            search_str = search_str.replace(/^\s\s*|^[\n\r]/g, '');
            if (regex_start.test(search_str) && search_str.length > self.options.min_charactor ){
                search_str = search_str.replace(pattern, '');
                return search_str.indexOf(' ') < 0 && !/[\r\n]/.test(search_str) ? search_str : false;
            }
            return false;
        };
        var desctiption = this.$textarea.val(),
        left_string = desctiption.substring(0, this.get_cursor_position(this.$textarea)),
        search_str = desctiption.substring(left_string.lastIndexOf("@") - 1, this.get_cursor_position(this.$textarea));
        return validate_keyword(search_str);
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
            }, this.options.typing_speed);
        }else if(this.$dropdown.find("li")){
            this.clear_dropdown();
        }
    },
    preprocess_mention_post: function(post_body, mention_callback){
        var mentions_partners = _.filter(this.selected_partners, function(partner){
            var word = _.str.sprintf("@%s", partner.name);
            if(post_body.indexOf(word) != -1) {
                post_body = post_body.replace(word, _.str.sprintf("@<span data-oe-model='res.partner' data-oe-id='%s'>%s</span> ", partner.id, partner.name));
                return true;
            }
        });
        // textarea text content should be format as HTML(preserve line breaks, spaces..). there is three option
        // 1) convert text to HTML in JS as we done at server side using plaintext2html.
        // 2) content_subtype as text and add condition in plaintext2html to stop escaping of specific @span tag.
        // 3) add message body inside pre tag.
        post_body = _.str.sprintf("<pre>%s</pre>", post_body);
        mention_callback(post_body, _.pluck(mentions_partners, 'id'));
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
            self.selected_partners.push({'id': partner.id, 'name': partner.name});
            var index = self.get_cursor_position(self.$textarea),
                value = self.$textarea.val();
            self.$textarea.val(_.str.sprintf("%s%s%s",
                    value.substring(0, index - self.search_string.length),
                    partner.name + " ",
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