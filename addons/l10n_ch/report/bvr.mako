<html>
<head>
       <style type="text/css">
           @font-face {
           	font-family: "bvrocrb";
           	font-style: normal;
           	font-weight: normal;
           	src: url(${police_absolute_path('ocrbb.ttf')}) format("truetype");
           }
           .ocrbb{
             text-align:right;
             font-family:bvrocrb;
             font-size:${str(company.bvr_scan_line_font_size or '0.0').replace(',','.')}pt;
             position:absolute;top:${str(company.bvr_scan_line_vert or '0.0').replace(',','.')}mm;
             left:${str(company.bvr_scan_line_horz or '0.0').replace(',','.')}mm;
             z-index:4;
             letter-spacing:str(company.bvr_scan_line_letter_spacing or '0.0').replace(',','.')
           }
        ${css}
    </style>
       </style>

   </head>
   <body topmargin="0px">
       <script type="text/javascript">
           function sortfunction(a, b){
            return (a.offsetTop - b.offsetTop) ;
           }
           function place_element2() {
               //This script was done to be inserted in any document mono or multi page some rounding problem may appear on mor than 10 page long report
               try{
                   //height of bvr in mm
                   var xpos = 105 + ${company.bvr_delta_horz or '0'};
                   //height of A4 page in bvr
                   var a4height = 297 ;
                   //should be insert a page
                   var insert_page = false; //will insert a blank page if true
                   // should we insert bvr background
                   var insert_bvrimg = ${str(company.bvr_background).lower()};
                   //horiz decalage
                   var vert_decalage = ${company.bvr_delta_vert or '0'};
                   // height of header
                   var headheight = ${headheight()};
                   //dpi resolution has found in wkhtmltopdf doc if you want to calculate it just create a div with one inch of width and retrieve is with in px
                   var res = 94; 
                   //we retriev all the bvr frame on the dom
                   var els_node_list = document.getElementsByName('bvrframe');
                   //we put them on an array
                   var els = [];
                   for(var i=0, len = els_node_list.length; i < len; i++)  
                   {  
                       els.push(els_node_list[i]);  
                   }
                   //we sort on y postiton values
                   els.sort(sortfunction);
                   for (var i=0; i<els.length; i++) {
                      var el = els[i];
                      var el_height_mm = el.offsetTop/(res/25.4);
                      // we insert the white page only if the BVR in not alleready on a separated page
                       //so we insert the white page only if the difference bettween the old posisition and the new posisition is < 297 mm
                      if(insert_page){
                             el_height_mm = el_height_mm + a4height;
                      }
                      
                      if(el_height_mm % xpos){
                          var el_xpos = Math.ceil(el_height_mm/a4height)*a4height;
                          //We compute the page  position of the a4 page on wich is the element.
                          // we substact the bvr height and the height of header*the number of pages and we add the vertical decalage
                          var ypos = (el_xpos-xpos)-(Math.ceil(el_height_mm/a4height)*headheight);

                          el.style.top = (ypos+vert_decalage)+"mm";
                          el.style.position = "absolute";
                 
                      } 
                      //This will propbely never happen but how knows ?
                      else {
                          var el_height_mm = el.offsetTop/(res/25.4);
                          el.style.top = (el_height_mm+vert_decalage)+"mm";
                          if(insert_page){
                              el.style.top = el.style.top + a4height
                          }
                      }
                      //we place the image if needed
                      if(insert_bvrimg){
                            img = document.getElementById("bvrimg_"+el.id);
                            img.style.top = el.style.top;
                            img.style.position = "absolute";
                      }
                   }
               } catch(err){
               //console.log(err)
              //document.getElementById("debug").textContent = document.getElementById("debug").textContent +"<br/>"+'-ERROR-'+err;
               }
           }
           window.onload=foo
           function foo() {
           place_element2();
           
           }
       </script>
       %for inv in objects :
       <% setLang(inv.partner_id.lang) %>
       <!--adresses + info block -->
            <table class="dest_address"  style="position:absolute;top:6mm;left:15mm">
               <tr><td ><b>${inv.partner_id.title.name or ''|entity}  ${inv.partner_id.name |entity}</b></td></tr>
               <tr><td>${inv.address_invoice_id.street or ''|entity}</td></tr>
               <tr><td>${inv.address_invoice_id.street2 or ''|entity}</td></tr>
               <tr><td>${inv.address_invoice_id.zip or ''|entity} ${inv.address_invoice_id.city or ''|entity}</td></tr>
               %if inv.address_invoice_id.country_id :
               <tr><td>${inv.address_invoice_id.country_id.name or ''|entity} </td></tr>
               %endif
               %if inv.address_invoice_id.phone :
               <tr><td>${_("Tel") |entity}: ${inv.address_invoice_id.phone|entity}</td></tr>
               %endif
               %if inv.address_invoice_id.fax :
               <tr><td>${_("Fax") |entity}: ${inv.address_invoice_id.fax|entity}</td></tr>
               %endif
               %if inv.address_invoice_id.email :
               <tr><td>${_("E-mail") |entity}: ${inv.address_invoice_id.email|entity}</td></tr>
               %endif
               %if inv.partner_id.vat :
               <tr><td>${_("VAT") |entity}: ${inv.partner_id.vat|entity}</td></tr>
               %endif
           </table>
       
       <div style="position:absolute;top:60mm; left:20mm">
           ${_('Invoice')} - ${inv.number or ''|entity}
           <br/>
           <br/>
           ${_('Here is the BVR to allow you to pay the invoice %s - %s') % (inv.name or '', inv.number or '',)}
           <br/>
           ${_('Regards')}
       </div>
       
       <div colspan="2" class="ocrbb">${mod10r('01'+str('%.2f' % inv.amount_total).replace('.','').rjust(10,'0'))}&gt;${_get_ref(inv)}+${inv.partner_bank_id.post_number.split('-')[0]+(str(inv.partner_bank_id.post_number.split('-')[1])).rjust(6,'0')+inv.partner_bank_id.post_number.split('-')[2]}&gt;</div>
       <div id="cont_${inv.id}" style="padding-left:20mm;padding-top:0;padding-bottom:10;height:180mm">
        <!-- Your communication message here -->
       </div>
    %if company.bvr_background:
    <img name="bvrimg" id="bvrimg_${inv.id}" alt="bvr" src="${bvr_absolute_path()}" style="width:210mm;height:106mm;border:0;margin:0;position:absolute;top:0" />
    %endif
    <table name="bvrframe"  id="${inv.id}" style="width:210mm;height:106mm;border-collapse:collapse;padding-left:3mm;font-family:Helvetica;font-size:8pt;border-width:0px" border="0" CELLPADDING="0" CELLSPACING="0"> <!--border-width:1px;border-style:solid;border-color:black;-->
        <tr style="height:16.933333mm;vertical-align:bottom;padding-bottom:3mm"><td style="width:60.14mm;padding-bottom:3mm"><div style="padding-left:3mm;">${inv.partner_bank_id and inv.partner_bank_id.print_bank and inv.partner_bank_id.bank and inv.partner_bank_id.bank.name or ''}</div></td><td style="width:60.96mm;padding-bottom:3mm"><div style="padding-left:3mm;">${inv.partner_bank_id and inv.partner_bank_id.print_bank and inv.partner_bank_id.bank and inv.partner_bank_id.bank.name or ''}</div></td><td style="width:88.9mm"></td></tr>
        <tr style="height:12.7mm;vertical-align:bottom;padding-bottom:3mm"><td style="width:60.14mm;padding-bottom:3mm"><div style="padding-left:3mm;"><b>${user.company_id.partner_id.name}</b></div></td><td style="width:60.96mm;padding-bottom:3mm"><div style="padding-left:3mm;"><b>${user.company_id.partner_id.name}</b></div></td><td style="width:88.9mm"></td></tr>
        <tr style="height:16.933333mm;vertical-align:bottom;padding-bottom:0"><td><table style="padding-left:3mm;font-family:Helvetica;font-size:8pt" height="100%"><tr style="vertical-align:top;padding-bottom:0"><td>${user.company_id.partner_id.address[0].street}<br/> ${user.company_id.partner_id.address[0].zip} ${user.company_id.partner_id.address[0].city}</td></tr><tr style="vertical-align:bottom;padding-bottom:0"><td><div style="padding-left:30.48mm;">${inv.partner_bank_id.print_account and inv.partner_bank_id.post_number or ''}</div></td></tr></table></td><td style="padding-left:3mm"><table style="padding-left:3mm;font-family:Helvetica;font-size:8pt" height="100%"><tr style="vertical-align:top;padding-bottom:0"><td>${user.company_id.partner_id.address[0].street}<br/>${user.company_id.partner_id.address[0].zip} ${user.company_id.partner_id.address[0].city}</td></tr><tr style="vertical-align:bottom;padding-bottom:0"><td><div style="padding-left:30.48mm;">${inv.partner_bank_id.print_account and inv.partner_bank_id.post_number or ''}</div></td></tr></table></td><td style="text-align: right;padding-right:4mm;padding-bottom:8mm;font-size:11pt">${_space(_get_ref(inv))}</td></tr>
        <tr style="height:8.4666667mm;vertical-align:bottom;padding-bottom:0"> <td><table  style="width:100%" CELLPADDING="0" CELLSPACING="0"><td  style="width:4mm"></td><td style="width:40mm;text-align: right" >${_space(('%.2f' % inv.amount_total)[:-3], 1)}</td><td style="width:6mm"></td><td style="width:10mm;text-align: right">${ _space(('%.2f' % inv.amount_total)[-2:], 1)}</td><td style="width:3mm;text-align: right"></td></table></td><td><table  style="width:100%" CELLPADDING="0" CELLSPACING="0"><td  style="width:4mm"></td><td style="width:40mm;text-align: right" >${_space(('%.2f' % inv.amount_total)[:-3], 1)}</td><td style="width:6mm"></td><td style="width:10mm;text-align: right">${ _space(('%.2f' % inv.amount_total)[-2:], 1)}</td><td style="width:3mm;text-align: right"></td></table></td><td></td></tr>
        <tr style="height:21.166667mm"><td></td><td></td><td></td></tr>
        <tr style="height:8.4666667mm"> <td></td><td></td><td></td></tr>
        <tr style="height:21.166667mm;vertical-align:top"><td></td><td></td></tr>
    </table>
    %endfor
</body>
</html>