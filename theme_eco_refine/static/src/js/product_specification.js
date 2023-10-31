odoo.define('theme_eco_refine.custom', function (require) {
    'use strict';
    var publicWidget = require('web.public.widget');
    publicWidget.registry.refurb_theme_product = publicWidget.Widget.extend({
        templates: 'website_sale.product',
        selector: '.tab',
        events: {
            'click .tab-link': 'openTab',
        },
        openTab: function (ev) {
           let tabId;
           if(this.$(ev.target).hasClass('tab1')){
                tabId = "tab1"
           }else{
              tabId = "tab2"
           }
          var tabContent = $(this.$el[0].parentNode.querySelectorAll(".tab-content"))
          var tabLinks = this.$el.find(".tab-link")
          for (var i = 0; i < tabContent.length; i++) {
            tabContent[i].style.display = "none";
          }
          for (var i = 0; i < tabLinks.length; i++) {
            tabLinks[i].classList.remove("active");
          }
          if(tabId){
            this.$el[0].parentNode.querySelectorAll("#"+tabId)[0].style.display = "block";
          }
          ev.target.classList.add("active");
        }
    });
    return publicWidget.registry.refurb_theme_product;
});
