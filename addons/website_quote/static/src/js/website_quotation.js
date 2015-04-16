(function () {
    'use strict';

    var website = openerp.website;
    website.quotation = {};

    website.if_dom_contains('div.o_website_quote', function () {

        // Add to SO button
        website.quotation.UpdateLineButton = openerp.Widget.extend({
            events: {
                'click' : 'onClick',
            },
            onClick: function(ev){
                ev.preventDefault();
                var self = this;
                var href = this.$el.attr("href");
                var order_id = href.match(/order_id=([0-9]+)/);
                var line_id = href.match(/update_line\/([0-9]+)/);
                var token = href.match(/token=(.*)/);
                openerp.jsonRpc("/quote/update_line", 'call', {
                    'line_id': line_id[1],
                    'order_id': parseInt(order_id[1]),
                    'token': token[1],
                    'remove': self.$el.is('[href*="remove"]'),
                    'unlink': self.$el.is('[href*="unlink"]')
                }).then(function (data) {
                    if(!data){
                        location.reload();
                    }
                    self.$el.parents('.input-group:first').find('.js_quantity').val(data[0]);
                    $('[data-id="total_amount"]>span').html(data[1]);
                });
                return false;
            },
        });

        var update_button_list = [];
        $('a.js_update_line_json').each(function( index ) {
            var button = new website.quotation.UpdateLineButton();
            button.setElement($(this)).start();
            update_button_list.push(button);
        });

        // Accept Modal, with jSignature
        website.quotation.AcceptModal = openerp.Widget.extend({
            events: {
                'shown.bs.modal': 'initSignature',
                'click #sign_clean': 'clearSignature',
                'submit #accept': 'submitForm',
            },
            initSignature: function(ev){
                this.$("#signature").empty().jSignature({'decor-color' : '#D1D0CE'});
                this.empty_sign = this.$("#signature").jSignature("getData",'image');
            },
            clearSignature: function(ev){
                this.$("#signature").jSignature('reset');
            },
            submitForm: function(ev){
                // extract data
                var self = this;
                var href = self.$el.find('form').attr("action");
                var action = href.match(/quote\/([a-z]+)/);
                var order_id = href.match(/quote\/[a-z]+\/([0-9]+)/);
                var token = href.match(/token=(.*)/);
                if (token){
                    token = token[1];
                }

                if (action[1]=='accept') {
                    ev.preventDefault();
                    // process : display errors, or submit
                    var signer_name = self.$("#name").val();
                    var signature = self.$("#signature").jSignature("getData",'image');
                    var is_empty = signature ? this.empty_sign[1] == signature[1] : false;
                    self.$('#signer').toggleClass('has-error', !signer_name);
                    self.$('#drawsign').toggleClass('panel-danger', is_empty).toggleClass('panel-default', !is_empty);
                    if (is_empty || ! signer_name){
                        return false;
                    }
                    openerp.jsonRpc("/quote/"+action[1], 'call', {
                        'order_id': parseInt(order_id[1]),
                        'token': token,
                        'signer': signer_name,
                        'sign': signature?JSON.stringify(signature[1]):false,
                    }).then(function (data) {
                        self.$el.modal('hide');
                        window.location.href = '/quote/'+order_id[1]+'/'+token+'?message=3';
                    });
                    return false;
                }
            },
        });

        var accept_modal = new website.quotation.AcceptModal();
        accept_modal.setElement($('#modalaccept'));
        accept_modal.start();

        // Nav Menu ScrollSpy
        website.quotation.NavigationSpyMenu = openerp.Widget.extend({
            start: function(watched_selector){
                this.authorized_text_tag = ['em', 'b', 'i', 'u'];
                this.spy_watched = $(watched_selector);
                this.generateMenu();
            },
            generateMenu: function(){
                var self = this;
                // reset ids
                $("[id^=quote_header_], [id^=quote_]", this.spy_watched).attr("id", "");
                // generate the new spy menu
                var last_li = false;
                var last_ul = null;
                _.each(this.spy_watched.find("h1, h2"), function(el){
                    switch (el.tagName.toLowerCase()) {
                        case "h1":
                            var id = self.setElementId('quote_header_', el);
                            var text = self.extractText($(el));
                            last_li = $("<li>").html('<a href="#'+id+'">'+text+'</a>').appendTo(self.$el);
                            last_ul = false;
                            break;
                        case "h2":
                            var id = self.setElementId('quote_', el);
                            var text = self.extractText($(el));
                            if (last_li) {
                                if (!last_ul) {
                                    last_ul = $("<ul class='nav'>").appendTo(last_li);
                                }
                                $("<li>").html('<a href="#'+id+'">'+text+'</a>').appendTo(last_ul);
                            }
                            break;
                    }
                });
            },
            setElementId: function(prefix, $el){
                var id = _.uniqueId(prefix);
                this.spy_watched.find($el).attr('id', id);
                return id;
            },
            extractText: function($node){
                var self = this;
                var raw_text = [];
                _.each($node.contents(), function(el){
                    var current = $(el);
                    if($.trim(current.text())){
                        var tagName = current.prop("tagName");
                        if(_.isUndefined(tagName) || (!_.isUndefined(tagName) && _.contains(self.authorized_text_tag, tagName.toLowerCase()))){
                            raw_text.push($.trim(current.text()));
                        }
                    }
                });
                return raw_text.join(' ');
            }
        });

        var nav_menu = new website.quotation.NavigationSpyMenu();
        nav_menu.setElement($('[data-id="quote_sidebar"]'));
        nav_menu.start($('body[data-target=".navspy"]'));

    });

}());

// dbo note: website_sale code for payment
// if we standardize payment somehow, this should disappear
$(document).ready(function () {

    // When choosing an acquirer, display its Pay Now button
    var $payment = $("#payment_method");
    $payment.on("click", "input[name='acquirer']", function (ev) {
            var payment_id = $(ev.currentTarget).val();
            $("div.oe_quote_acquirer_button[data-id]", $payment).addClass("hidden");
            $("div.oe_quote_acquirer_button[data-id='"+payment_id+"']", $payment).removeClass("hidden");
        })
        .find("input[name='acquirer']:checked").click();

    // When clicking on payment button: create the tx using json then continue to the acquirer
    $payment.on("click", 'button[type="submit"],button[name="submit"]', function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      var $form = $(ev.currentTarget).parents('form');
      var acquirer_id = $(ev.currentTarget).parents('div.oe_quote_acquirer_button').first().data('id');
      if (! acquirer_id) {
        return false;
      }
      var href = $(location).attr("href");
      var order_id = href.match(/quote\/([0-9]+)/)[1];
      openerp.jsonRpc('/quote/' + order_id +'/transaction/' + acquirer_id, 'call', {}).then(function (data) {
        $form.submit();
      });
   });

});
