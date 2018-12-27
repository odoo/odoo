[1mdiff --cc addons/website_sale/static/src/js/website_sale.editor.js[m
[1mindex c718a87172c,823cdd5aa87..00000000000[m
[1m--- a/addons/website_sale/static/src/js/website_sale.editor.js[m
[1m+++ b/addons/website_sale/static/src/js/website_sale.editor.js[m
[36m@@@ -74,6 -74,7 +74,10 @@@[m [moptions.registry.website_sale = options[m
          var size_x = parseInt(this.$target.attr("colspan") || 1);[m
          var size_y = parseInt(this.$target.attr("rowspan") || 1);[m
  [m
[32m++<<<<<<< HEAD[m
[32m++=======[m
[32m+         var $changePpr = this.$el.find('div[name="o_website_sale_change_ppr"]');[m
[32m++>>>>>>> imp grid layout[m
  [m
          var $size = this.$el.find('div[name="size"]');[m
          var $select = $size.find('tr:eq(0) td:lt('+size_x+')');[m
[36m@@@ -82,10 -83,17 +86,24 @@@[m
          if (size_y >= 4) $select = $select.add($size.find('tr:eq(3) td:lt('+size_x+')'));[m
          $select.addClass("selected");[m
  [m
[32m++<<<<<<< HEAD[m
[32m +        var ppr = parseInt(this.$('[ppr]').attr("ppr"));[m
[32m +[m
[32m +        // add active class to currently selected ppr[m
[32m +        this.$el.find('.o_website_sale_ppr_select a[data-nbr_col="' + ppr + '"]').addClass('active');[m
[32m++=======[m
[32m+         var ppr = parseInt(this.$target.attr("ppr"));[m
[32m+ [m
[32m+         // add active class to currently selected ppr[m
[32m+         $changePpr.find('a').each(function () {[m
[32m+             var $a = $(this);[m
[32m+             if ($a.data('nbr_col') === ppr) {[m
[32m+                 $a.addClass('active');[m
[32m+             } else {[m
[32m+                 $a.removeClass('active');[m
[32m+             }[m
[32m+         });[m
[32m++>>>>>>> imp grid layout[m
  [m
          // Adapt size array preview to fit ppr[m
          $size.find('tr').each(function (index) {[m
[1mdiff --cc addons/website_sale/views/snippets.xml[m
[1mindex 3a69dcf825d,6a6c13f7b75..00000000000[m
[1m--- a/addons/website_sale/views/snippets.xml[m
[1m+++ b/addons/website_sale/views/snippets.xml[m
[36m@@@ -8,7 -8,7 +8,11 @@@[m
              data-no-check="true">[m
              <div class='dropdown-submenu' role="menuitem" aria-haspopup="true">[m
                  <a tabindex="-1" href="#" class="dropdown-item">Number of Columns</a>[m
[32m++<<<<<<< HEAD[m
[32m +                <div class="dropdown-menu o_website_sale_ppr_select" role="menu" data-no-preview="true">[m
[32m++=======[m
[32m+                 <div class="dropdown-menu o_website_sale_change_ppr" role="menu" data-no-preview="true">[m
[32m++>>>>>>> imp grid layout[m
                      <a href="#" class="dropdown-item" role="menuitem" data-nbr_col="2">2 Columns</a>[m
                      <a href="#" class="dropdown-item" role="menuitem" data-nbr_col="3">3 Columns</a>[m
                      <a href="#" class="dropdown-item" role="menuitem" data-nbr_col="4">4 Columns</a>[m
