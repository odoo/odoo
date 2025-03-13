[1mdiff --git a/addons/sale/models/sale_order.py b/addons/sale/models/sale_order.py[m
[1mindex 88e519b15c82..016db817761c 100644[m
[1m--- a/addons/sale/models/sale_order.py[m
[1m+++ b/addons/sale/models/sale_order.py[m
[36m@@ -1390,27 +1390,22 @@[m [mclass SaleOrder(models.Model):[m
 [m
     def _get_invoiceable_lines(self, final=False):[m
         """Return the invoiceable lines for order `self`."""[m
[31m-        current_section_line_ids = [][m
         down_payment_line_ids = [][m
         invoiceable_line_ids = [][m
[31m-        pending_section = None[m
[32m+[m[32m        current_section = None[m
         precision = self.env['decimal.precision'].precision_get('Product Unit')[m
[32m+[m[32m        section_line_ids = [][m
 [m
         for line in self.order_line:[m
             if line.display_type == 'line_section':[m
                 # Only invoice the section if one of its lines is invoiceable[m
[31m-                if current_section_line_ids:[m
[31m-                    if not any([m
[31m-                        not temp_line.display_type[m
[31m-                        for temp_line in self.env['sale.order.line'].browse([m
[31m-                            current_section_line_ids[m
[32m+[m[32m                if section_line_ids:[m
[32m+[m[32m                    if any(not section_line.display_type for section_line in section_line_ids):[m
[32m+[m[32m                        invoiceable_line_ids.extend([m
[32m+[m[32m                            [section_line.id for section_line in section_line_ids][m
                         )[m
[31m-                    ):[m
[31m-                        current_section_line_ids.clear()[m
[31m-                    else:[m
[31m-                        invoiceable_line_ids.extend(current_section_line_ids)[m
[31m-                        current_section_line_ids.clear()[m
[31m-                pending_section = line[m
[32m+[m[32m                current_section = line[m
[32m+[m[32m                section_line_ids = [current_section][m
                 continue[m
             if line.display_type != 'line_note' and float_is_zero(line.qty_to_invoice, precision_digits=precision):[m
                 continue[m
[36m@@ -1420,22 +1415,13 @@[m [mclass SaleOrder(models.Model):[m
                     # at the end of the invoice, in a specific dedicated section.[m
                     down_payment_line_ids.append(line.id)[m
                     continue[m
[31m-                if pending_section:[m
[31m-                    current_section_line_ids.append(pending_section.id)[m
[31m-                    pending_section = None[m
[31m-                current_section_line_ids.append(line.id)[m
[31m-[m
[31m-        if current_section_line_ids:[m
[31m-            if not any([m
[31m-                not temp_line.display_type[m
[31m-                for temp_line in self.env['sale.order.line'].browse([m
[31m-                    current_section_line_ids[m
[31m-                )[m
[31m-            ):[m
[31m-                current_section_line_ids.clear()[m
[31m-            else:[m
[31m-                invoiceable_line_ids.extend(current_section_line_ids)[m
[31m-                current_section_line_ids.clear()[m
[32m+[m[32m                if current_section:[m
[32m+[m[32m                    section_line_ids.append(line)[m
[32m+[m[32m                else:[m
[32m+[m[32m                    invoiceable_line_ids.append(line.id)[m
[32m+[m
[32m+[m[32m        if any(not section_line.display_type for section_line in section_line_ids):[m
[32m+[m[32m            invoiceable_line_ids.extend([section_line.id for section_line in section_line_ids])[m
 [m
         return self.env['sale.order.line'].browse(invoiceable_line_ids + down_payment_line_ids)[m
 [m
