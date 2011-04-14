openerp.web_chat = function (openerp) {
    openerp.web_chat = {};
    openerp.web_chat.im = new AjaxIM({
       storageMethod: 'local',
       pollServer: '/web_chat/pollserver',
       theme: '/web_chat/static/lib/AjaxIM/themes/default',
       flashStorage: '/web_chat/static/lib/AjaxIM/js/jStore.Flash.html'
    });
    openerp.web_chat.im.login();
};
