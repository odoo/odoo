odoo.define('point_of_sale.editor', function (require) {
    'use strict';

    var Editor = require('web_editor.snippet.editor').Editor;
    var s_options = require('web_editor.snippets.options');

    var core = require('web.core');
    var _t = core._t;

    // Clone default web_editor background image functionalities
    s_options.registry.pos_background = s_options.registry.background;

    // Show reset button for company logo
    s_options.registry.pos_company_logo = s_options.Class.extend({
        start: function () {
            var self = this;
            setTimeout(function(){
                self.$overlay.find('.pos-use_default_logo').removeClass("hidden");
            },500);
        }
    });

    s_options.registry.pos_no_parent = s_options.Class.extend({
        start:function() {
            this.$overlay.find('.oe_options').addClass('no_parent_options');
            this.$overlay.find('.oe_overlay_options').css({'top':'0px'});
        }
    });

    // Hide 'remove' buttun for element that should not be removed
    s_options.registry.pos_no_remove = s_options.Class.extend({
        start:function() {
            this.$overlay.find('.oe_snippet_remove').addClass('hidden');
            this.$('.pos-adv').append($('<div class="pos_adv_onsave_remove text-center" style="color:#666666; padding:10px;">' + _t('Set your customized advertisement here') + '</span>'));
        },

        clean_for_save: function() {
            this.$('.pos_adv_onsave_remove').remove();
        }
    });

    // Palette
    s_options.registry.pos_palette = s_options.Class.extend({
        start:function() {
            this.$overlay.find('.oe_overlay_options').css({'top':'0px', 'left': 'calc(50% - 45px)'}).end()
                         .find('.oe_options').addClass('snippet-option-pos_palette')
                         .find('> a').text('Palette').prepend('<i style="margin-right:5px" class="fa fa-paint-brush"/>');
        }
    });

});