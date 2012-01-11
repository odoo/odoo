/*############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011-2012 OpenERP SA (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
############################################################################*/

var __lc_buttons = [];

openerp.web_livechat = function (openerp) {

openerp.web_livechat.Livechat = openerp.web.Widget.extend({
    template: 'Header-LiveChat',

    start: function() {
        this._super();
        if (!this.session)
            return;
        var self = this;
        var pwc = new openerp.web.Model("publisher_warranty.contract");
        return pwc.get_func('get_default_livechat_text')().then(function(text) {
            self.$element.html(text);
            pwc.get_func('is_livechat_enable')().then(function(res) {
                if(res) {
                    self.$element.click(self.do_load_livechat);
                } else {
                    self.$element.click(self.do_open_url);
                }
            })
        });
    },

    do_open_url: function(evt) {
        evt.preventDefault();    
        openerp.webclient.action_manager.do_action({type: 'ir.actions.act.url', url: 'http://www.openerp.com/support-or-publisher-warranty-contract', target: 'new'});
    },

    do_load_livechat: function(evt) {
        evt.preventDefault();    
        var self = this;

        this.$element.unbind('click', this.do_load_livechat);

        var lc_id = _.uniqueId('livechat_');
        this.$element.attr('id', lc_id);

        var pwc = new openerp.web.Model("publisher_warranty.contract");
        
        pwc.get_func('is_livechat_enable')().then(function(res) {
            console.log('res', res);
            if(!res) {
                return;
            }

            // connect to LiveChat
            __lc_load();

            __lc_buttons.push({
                elementId: lc_id, //'livechat_status',
                language: 'en',
                skill: '0',
                type: 'text',
                labels: {
                    online: '<img src="/web_livechat/static/src/img/available.png"/>Support',
                    offline: '<img src="/web_livechat/static/src/img/away.png"/>Support',
                }
            });
        });
    }
});


openerp.web.Header.include({
    do_update: function() {
        var self = this;
        this._super();
        this.update_promise.then(function() {
            if (self.livechat) {
                self.livechat.stop();
            }
            self.livechat = new openerp.web_livechat.Livechat(self);
            self.livechat.prependTo(self.$element.find('div.header_corner'));
        });
    }
});




if (openerp.webclient) {
    // tracking code from LiveChat
    var license = '1035052',
        params = '',
        lang = 'en',
        skill = '0';
    __lc_load = function (p) { 
      if (typeof __lc_loaded != 'function')
        if (p) { 
          var d = document,
            l = d.createElement('script'),
            s = d.getElementsByTagName('script')[0],
            a = unescape('%26'),
            h = ('https:' == d.location.protocol ? 'https://' : 'http://');
          l.type = 'text/javascript';
          l.async = true;
          l.src = h + 'gis' + p +'.livechatinc.com/gis.cgi?serverType=control'+a+'licenseID='+license+a+'jsonp=__lc_load';
          if (!(typeof p['server'] !== 'string' || typeof __lc_serv === 'string')) {
            l.src = h + (__lc_serv = p['server']) + '/licence/'+license+'/script.cgi?lang='+lang+a+'groups='+skill;
            l.src += (params == '') ? '' : a+'params='+encodeURIComponent(encodeURIComponent(params));
            s.parentNode.insertBefore(l, s);
          } else 
            setTimeout(__lc_load, 1000);
          if(typeof __lc_serv != 'string'){
            s.parentNode.insertBefore(l, s);
          }
        } else __lc_load(Math.ceil(Math.random()*5));
    }
}

};
