#!/bin/sh

barcode -t 2x7+40+40 -m 50x30 -p "210x297mm" -e code128b -n > barcodes_actions_barcode.ps << BARCODES
O-CMD.MAIN-MENU
O-CMD.DISCARD
O-BTN.validate
O-CMD.cancel
O-BTN.print-mo
O-BTN.print-product-label
O-BTN.scrap
BARCODES

cat > barcodes_actions_header.ps << HEADER
/showTitle { /Helvetica findfont 12 scalefont setfont moveto show } def
(MAIN MENU) 89 768 showTitle
(DISCARD) 348 768 showTitle
(PRODUCE) 89 660 showTitle
(CANCEL) 348 660 showTitle
(PRINT PRODUCTION ORDER) 89 551 showTitle
(PRINT FINISHED PRODUCT LABEL) 348 551 showTitle
(SCRAP) 89 444 showTitle

HEADER

cat barcodes_actions_header.ps barcodes_actions_barcode.ps | ps2pdf - - > barcodes_mrp_actions.pdf
rm barcodes_actions_header.ps barcodes_actions_barcode.ps
