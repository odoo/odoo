openerp.website = function(instance) {

instance.website.EditorBar = instance.web.Widget.extend({
    template: 'Website.EditorBar',
    events: {
        'click button[data-action=edit]': 'edit',
        'click button[data-action=save]': 'save',
        'click button[data-action=cancel]': 'cancel',
    },
    container: 'body',
    start: function() {
        var self = this;
        self.$('button[data-action]').prop('disabled', true);
        self.$('button[data-action=edit]').prop('disabled', false);
        return this._super.apply(this, arguments);
    },
    edit: function () {
        var self = this;
        Aloha.ready(function() {
            Aloha.jQuery('[data-oe-model]').aloha(); //.attr('contentEditable', 'true').addClass('oe_editable');
            self.$('button').prop('disabled', true);
            self.$('button[data-action=save],button[data-action=cancel]').prop('disabled', false);
            Aloha.bind('aloha-editable-activated', function (ev, args) {
                var $e = args.editable.obj;
                if (!$e.is('.oe_dirty')) {
                    $e.addClass('oe_dirty');
                    // TODO: Are we going to use a meta-data flag in order to know if the field shall be text or html ?
                    $e.data('original', $e.html());
                }
            });
        });
    },
    save: function () {
        var self = this;
        var defs = [];
        $('.oe_dirty').each(function () {
            var $el = $(this);
            var def = self.saveElement($el).then(function () {
                $el.removeClass('oe_dirty');
            }).fail(function () {
                var data = $el.data();
                console.error(_.str.sprintf('Could not save %s#%d#%s', data.oeModel, data.oeId, data.oeField));
            });
            defs.push(def);
        });
        return $.when.apply(null, defs).then(function () {
            window.location.reload();
        });
    },
    saveElement: function ($el) {
        var data = $el.data();
        var html = $el.html();
        var xpath = data.oeXpath;
        if (xpath) {
            var $w = $el.clone();
            $w.removeClass('aloha-editable aloha-editable-highlight oe_dirty');
            _.each(['model', 'id', 'field', 'xpath'], function(d) {$w.removeAttr('data-oe-' + d);});
            html = $w.wrap('<div>').parent().html();
        }
        return (new instance.web.DataSet(this, 'ir.ui.view')).call('save', [data.oeModel, data.oeId, data.oeField, html, xpath]);
    },
    cancel: function () {
        window.location.reload();
    }
});

$(function(){

    var selected_snippet = null;
    function snippet_click(event){
        if(selected_snippet){
            selected_snippet.removeClass('oe_selected');
            if(selected_snippet[0] === $(this)[0]){
                selected_snippet = null;
                event.preventDefault();
                make_static();
                return;
            }
        }
        $(this).addClass('oe_selected');
        selected_snippet = $(this);
        make_editable();
        event.preventDefault();
    }
    //$('.oe_snippet').click(snippet_click);

    var hover_element = null;

    function make_editable( constraint_after, constraint_inside ){
        if(selected_snippet && selected_snippet.hasClass('oe_new')){
            $('.oe_snippet_demo').addClass('oe_new');
        }else{
            $('.oe_snippet_demo').removeClass('oe_new');
        }
    
        $('.oe_page *').off('mouseover');
        $('.oe_page *').off('mouseleave');
        $('.oe_page *').mouseover(function(event){
            console.log('hover:',this);
            if(hover_element){
                hover_element.removeClass('oe_selected');
                hover_element.off('click');
            }
            $(this).addClass('oe_selected');
            $(this).click(append_snippet);
            hover_element = $(this);
            event.stopPropagation();
        });
        $('.oe_page *').mouseleave(function(){
            if(hover_element && $(this) === hover_element){
                hover_element = null;
                $(this).removeClass('oe_selected');
            }
        });
    }

    function make_static(){
        $('.oe_snippet_demo').removeClass('oe_new');
        $('.oe_page *').off('mouseover');
        $('.oe_page *').off('mouseleave');
        $('.oe_page .oe_selected').removeClass('oe_selected');
    }
        

    function append_snippet(event){
        console.log('click',this,event.button);
        if(event.button === 0){
            if(selected_snippet){
                if(selected_snippet.hasClass('oe_new')){
                    var new_snippet = $("<div class='oe_snippet'></div>");
                    new_snippet.append($(this).clone());
                    new_snippet.click(snippet_click);
                    $('.oe_snippet.oe_selected').before(new_snippet);
                }else{
                    $(this).after($('.oe_snippet.oe_selected').contents().clone());
                }
                selected_snippet.removeClass('oe_selected');
                selected_snippet = null;
                make_static();
            }
        }else if(event.button === 1){
            $(this).remove();
        }
        event.preventDefault();
    }

});

};
